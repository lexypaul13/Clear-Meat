"""Performance monitoring service for tracking optimization metrics."""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
import asyncio
from contextlib import contextmanager

from app.core.cache import cache

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Represents a single performance measurement."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class APICallMetrics:
    """Metrics for API calls."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_response_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    @property
    def success_rate(self) -> float:
        return (self.successful_calls / self.total_calls * 100) if self.total_calls > 0 else 0.0
    
    @property
    def average_response_time(self) -> float:
        return (self.total_response_time / self.total_calls) if self.total_calls > 0 else 0.0
    
    @property
    def cache_hit_rate(self) -> float:
        total_cache_requests = self.cache_hits + self.cache_misses
        return (self.cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0.0


class PerformanceMonitor:
    """Monitors and tracks application performance metrics."""
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize performance monitor.
        
        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history
        self.lock = threading.RLock()
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=max_history)
        self.api_metrics: Dict[str, APICallMetrics] = defaultdict(APICallMetrics)
        
        # Response time tracking (last 100 requests per endpoint)
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Database query tracking
        self.db_query_times: deque = deque(maxlen=100)
        self.slow_queries: List[Dict[str, Any]] = []
        
        # AI/Gemini call tracking
        self.ai_call_metrics = APICallMetrics()
        self.gemini_call_history: deque = deque(maxlen=50)
        
        logger.info(f"Performance monitor initialized with history size: {max_history}")
    
    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a performance metric."""
        with self.lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=datetime.now(),
                tags=tags or {}
            )
            self.metrics_history.append(metric)
    
    def record_api_call(
        self, 
        endpoint: str, 
        response_time: float, 
        success: bool,
        cache_hit: bool = False
    ):
        """Record API call metrics."""
        with self.lock:
            metrics = self.api_metrics[endpoint]
            metrics.total_calls += 1
            metrics.total_response_time += response_time
            
            if success:
                metrics.successful_calls += 1
            else:
                metrics.failed_calls += 1
            
            if cache_hit:
                metrics.cache_hits += 1
            else:
                metrics.cache_misses += 1
            
            # Track response times for percentile calculations
            self.response_times[endpoint].append(response_time)
            
            # Record as general metric
            self.record_metric(
                f"api_response_time",
                response_time,
                {"endpoint": endpoint, "success": str(success)}
            )
    
    def record_gemini_call(
        self, 
        call_type: str, 
        response_time: float, 
        success: bool,
        tokens_used: Optional[int] = None,
        was_batched: bool = False
    ):
        """Record Gemini AI API call metrics."""
        with self.lock:
            self.ai_call_metrics.total_calls += 1
            self.ai_call_metrics.total_response_time += response_time
            
            if success:
                self.ai_call_metrics.successful_calls += 1
            else:
                self.ai_call_metrics.failed_calls += 1
            
            # Record detailed call info
            call_info = {
                "type": call_type,
                "response_time": response_time,
                "success": success,
                "tokens_used": tokens_used,
                "was_batched": was_batched,
                "timestamp": datetime.now()
            }
            self.gemini_call_history.append(call_info)
            
            # Record as metric
            self.record_metric(
                f"gemini_call_time",
                response_time,
                {
                    "type": call_type, 
                    "success": str(success),
                    "batched": str(was_batched)
                }
            )
    
    def record_database_query(self, query_time: float, query_type: str = "unknown"):
        """Record database query metrics."""
        with self.lock:
            self.db_query_times.append(query_time)
            
            # Track slow queries (>1 second)
            if query_time > 1.0:
                slow_query = {
                    "query_time": query_time,
                    "query_type": query_type,
                    "timestamp": datetime.now()
                }
                self.slow_queries.append(slow_query)
                
                # Keep only last 20 slow queries
                if len(self.slow_queries) > 20:
                    self.slow_queries.pop(0)
            
            self.record_metric(
                "database_query_time",
                query_time,
                {"type": query_type}
            )
    
    def record_cache_operation(self, operation: str, hit: bool, response_time: float = 0.0):
        """Record cache operation metrics."""
        with self.lock:
            self.record_metric(
                "cache_operation_time",
                response_time,
                {"operation": operation, "hit": str(hit)}
            )
    
    def get_endpoint_stats(self, endpoint: str) -> Dict[str, Any]:
        """Get statistics for a specific endpoint."""
        with self.lock:
            if endpoint not in self.api_metrics:
                return {}
            
            metrics = self.api_metrics[endpoint]
            response_times = list(self.response_times[endpoint])
            
            stats = {
                "total_calls": metrics.total_calls,
                "success_rate": metrics.success_rate,
                "average_response_time": metrics.average_response_time,
                "cache_hit_rate": metrics.cache_hit_rate,
                "response_times": {
                    "min": min(response_times) if response_times else 0,
                    "max": max(response_times) if response_times else 0,
                    "p50": self._percentile(response_times, 50) if response_times else 0,
                    "p95": self._percentile(response_times, 95) if response_times else 0,
                    "p99": self._percentile(response_times, 99) if response_times else 0,
                }
            }
            
            return stats
    
    def get_gemini_stats(self) -> Dict[str, Any]:
        """Get Gemini API call statistics."""
        with self.lock:
            metrics = self.ai_call_metrics
            recent_calls = list(self.gemini_call_history)
            
            # Calculate batch efficiency
            total_calls = len(recent_calls)
            batched_calls = sum(1 for call in recent_calls if call.get("was_batched", False))
            batch_efficiency = (batched_calls / total_calls * 100) if total_calls > 0 else 0.0
            
            # Response time stats
            response_times = [call["response_time"] for call in recent_calls if call["success"]]
            
            stats = {
                "total_calls": metrics.total_calls,
                "success_rate": metrics.success_rate,
                "average_response_time": metrics.average_response_time,
                "batch_efficiency": batch_efficiency,
                "response_times": {
                    "min": min(response_times) if response_times else 0,
                    "max": max(response_times) if response_times else 0,
                    "p50": self._percentile(response_times, 50) if response_times else 0,
                    "p95": self._percentile(response_times, 95) if response_times else 0,
                },
                "call_types": self._get_call_type_breakdown(recent_calls)
            }
            
            return stats
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database performance statistics."""
        with self.lock:
            query_times = list(self.db_query_times)
            
            stats = {
                "total_queries": len(query_times),
                "average_query_time": sum(query_times) / len(query_times) if query_times else 0,
                "slow_queries_count": len(self.slow_queries),
                "query_times": {
                    "min": min(query_times) if query_times else 0,
                    "max": max(query_times) if query_times else 0,
                    "p50": self._percentile(query_times, 50) if query_times else 0,
                    "p95": self._percentile(query_times, 95) if query_times else 0,
                },
                "recent_slow_queries": self.slow_queries[-5:]  # Last 5 slow queries
            }
            
            return stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        with self.lock:
            # Overall API performance
            total_api_calls = sum(m.total_calls for m in self.api_metrics.values())
            total_successful = sum(m.successful_calls for m in self.api_metrics.values())
            total_cache_hits = sum(m.cache_hits for m in self.api_metrics.values())
            total_cache_requests = sum(m.cache_hits + m.cache_misses for m in self.api_metrics.values())
            
            summary = {
                "api_performance": {
                    "total_calls": total_api_calls,
                    "overall_success_rate": (total_successful / total_api_calls * 100) if total_api_calls > 0 else 0,
                    "overall_cache_hit_rate": (total_cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0,
                },
                "gemini_performance": self.get_gemini_stats(),
                "database_performance": self.get_database_stats(),
                "top_endpoints": self._get_top_endpoints_by_calls(),
                "slowest_endpoints": self._get_slowest_endpoints(),
            }
            
            return summary
    
    def export_metrics(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Export metrics for external analysis."""
        with self.lock:
            if since is None:
                since = datetime.now() - timedelta(hours=1)  # Last hour by default
            
            filtered_metrics = [
                {
                    "name": metric.name,
                    "value": metric.value,
                    "timestamp": metric.timestamp.isoformat(),
                    "tags": metric.tags
                }
                for metric in self.metrics_history
                if metric.timestamp >= since
            ]
            
            return filtered_metrics
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self.lock:
            self.metrics_history.clear()
            self.api_metrics.clear()
            self.response_times.clear()
            self.db_query_times.clear()
            self.slow_queries.clear()
            self.ai_call_metrics = APICallMetrics()
            self.gemini_call_history.clear()
            
            logger.info("Performance metrics reset")
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a list of numbers."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        else:
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
    
    def _get_call_type_breakdown(self, calls: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of call types."""
        breakdown = defaultdict(int)
        for call in calls:
            breakdown[call.get("type", "unknown")] += 1
        return dict(breakdown)
    
    def _get_top_endpoints_by_calls(self) -> List[Dict[str, Any]]:
        """Get top endpoints by call count."""
        endpoint_stats = [
            {
                "endpoint": endpoint,
                "calls": metrics.total_calls,
                "success_rate": metrics.success_rate
            }
            for endpoint, metrics in self.api_metrics.items()
        ]
        
        return sorted(endpoint_stats, key=lambda x: x["calls"], reverse=True)[:5]
    
    def _get_slowest_endpoints(self) -> List[Dict[str, Any]]:
        """Get slowest endpoints by average response time."""
        endpoint_stats = [
            {
                "endpoint": endpoint,
                "average_response_time": metrics.average_response_time,
                "calls": metrics.total_calls
            }
            for endpoint, metrics in self.api_metrics.items()
            if metrics.total_calls > 0
        ]
        
        return sorted(endpoint_stats, key=lambda x: x["average_response_time"], reverse=True)[:5]


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


@contextmanager
def track_api_call(endpoint: str, cache_hit: bool = False):
    """Context manager to track API call performance."""
    monitor = get_performance_monitor()
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception as e:
        success = False
        raise
    finally:
        response_time = time.time() - start_time
        monitor.record_api_call(endpoint, response_time, success, cache_hit)


@contextmanager
def track_database_query(query_type: str = "unknown"):
    """Context manager to track database query performance."""
    monitor = get_performance_monitor()
    start_time = time.time()
    
    try:
        yield
    finally:
        query_time = time.time() - start_time
        monitor.record_database_query(query_time, query_type)


@contextmanager
def track_gemini_call(call_type: str, was_batched: bool = False):
    """Context manager to track Gemini API call performance."""
    monitor = get_performance_monitor()
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception as e:
        success = False
        raise
    finally:
        response_time = time.time() - start_time
        monitor.record_gemini_call(call_type, response_time, success, was_batched=was_batched) 