"""Performance monitoring and dashboard endpoints."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.performance_monitor import get_performance_monitor
from app.core.cache import cache

router = APIRouter()


@router.get("/summary", response_model=Dict[str, Any])
def get_performance_summary() -> Dict[str, Any]:
    """
    Get overall performance summary.
    
    Returns comprehensive performance metrics including:
    - API call statistics
    - Gemini AI performance
    - Database query performance
    - Cache hit rates
    """
    monitor = get_performance_monitor()
    return monitor.get_performance_summary()


@router.get("/api/{endpoint:path}", response_model=Dict[str, Any])
def get_endpoint_performance(endpoint: str) -> Dict[str, Any]:
    """
    Get performance statistics for a specific API endpoint.
    
    Args:
        endpoint: The API endpoint path to analyze
        
    Returns:
        Detailed performance metrics for the endpoint
    """
    monitor = get_performance_monitor()
    stats = monitor.get_endpoint_stats(endpoint)
    
    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"No performance data found for endpoint: {endpoint}"
        )
    
    return {
        "endpoint": endpoint,
        "statistics": stats
    }


@router.get("/gemini", response_model=Dict[str, Any])
def get_gemini_performance() -> Dict[str, Any]:
    """
    Get Gemini AI API performance statistics.
    
    Returns:
        Detailed metrics about AI call performance including:
        - Success rates
        - Response times
        - Batch efficiency
        - Call type breakdown
    """
    monitor = get_performance_monitor()
    return {
        "gemini_ai_performance": monitor.get_gemini_stats()
    }


@router.get("/database", response_model=Dict[str, Any])
def get_database_performance() -> Dict[str, Any]:
    """
    Get database performance statistics.
    
    Returns:
        Database query performance metrics including:
        - Query times
        - Slow query analysis
        - Performance percentiles
    """
    monitor = get_performance_monitor()
    return {
        "database_performance": monitor.get_database_stats()
    }


@router.get("/cache", response_model=Dict[str, Any])
def get_cache_performance() -> Dict[str, Any]:
    """
    Get cache performance statistics.
    
    Returns:
        Cache performance metrics including hit rates and efficiency
    """
    # Get cache stats from the global cache instance
    cache_stats = {
        "redis_available": cache.redis_client is not None,
        "local_cache_size": len(cache.local_cache),
        "cache_operations": "Available in detailed metrics"
    }
    
    # Add recent cache metrics from performance monitor
    monitor = get_performance_monitor()
    recent_metrics = monitor.export_metrics(since=datetime.now() - timedelta(minutes=15))
    
    cache_metrics = [m for m in recent_metrics if m["name"] == "cache_operation_time"]
    
    if cache_metrics:
        hit_count = len([m for m in cache_metrics if m["tags"].get("hit") == "True"])
        miss_count = len([m for m in cache_metrics if m["tags"].get("hit") == "False"])
        total_operations = hit_count + miss_count
        
        cache_stats.update({
            "recent_operations": total_operations,
            "recent_hit_rate": (hit_count / total_operations * 100) if total_operations > 0 else 0,
            "recent_hits": hit_count,
            "recent_misses": miss_count
        })
    
    return {
        "cache_performance": cache_stats
    }


@router.get("/metrics/export", response_model=Dict[str, Any])
def export_performance_metrics(
    hours: int = Query(1, ge=1, le=24, description="Number of hours of metrics to export"),
    metric_name: Optional[str] = Query(None, description="Filter by specific metric name")
) -> Dict[str, Any]:
    """
    Export raw performance metrics for external analysis.
    
    Args:
        hours: Number of hours of historical data to include
        metric_name: Optional filter for specific metric types
        
    Returns:
        Raw metrics data suitable for analysis tools
    """
    monitor = get_performance_monitor()
    since = datetime.now() - timedelta(hours=hours)
    
    all_metrics = monitor.export_metrics(since=since)
    
    # Filter by metric name if specified
    if metric_name:
        all_metrics = [m for m in all_metrics if m["name"] == metric_name]
    
    # Calculate summary statistics
    metric_summary = {}
    for metric in all_metrics:
        name = metric["name"]
        if name not in metric_summary:
            metric_summary[name] = {
                "count": 0,
                "avg_value": 0,
                "min_value": float('inf'),
                "max_value": float('-inf'),
                "total_value": 0
            }
        
        summary = metric_summary[name]
        value = metric["value"]
        summary["count"] += 1
        summary["total_value"] += value
        summary["min_value"] = min(summary["min_value"], value)
        summary["max_value"] = max(summary["max_value"], value)
        summary["avg_value"] = summary["total_value"] / summary["count"]
    
    return {
        "export_parameters": {
            "hours": hours,
            "metric_filter": metric_name,
            "total_metrics": len(all_metrics),
            "export_timestamp": datetime.now().isoformat()
        },
        "metric_summary": metric_summary,
        "raw_metrics": all_metrics
    }


@router.get("/optimization-impact", response_model=Dict[str, Any])
def get_optimization_impact() -> Dict[str, Any]:
    """
    Get analysis of optimization impact and recommendations.
    
    Returns:
        Analysis of current optimizations and recommendations for improvement
    """
    monitor = get_performance_monitor()
    gemini_stats = monitor.get_gemini_stats()
    db_stats = monitor.get_database_stats()
    summary = monitor.get_performance_summary()
    
    # Calculate optimization metrics
    cache_hit_rate = summary.get("api_performance", {}).get("overall_cache_hit_rate", 0)
    batch_efficiency = gemini_stats.get("batch_efficiency", 0)
    avg_response_time = gemini_stats.get("average_response_time", 0)
    
    # Generate optimization recommendations
    recommendations = []
    
    if cache_hit_rate < 70:
        recommendations.append({
            "type": "cache",
            "priority": "high",
            "message": f"Cache hit rate is {cache_hit_rate:.1f}%. Consider increasing cache TTL or improving cache key strategies."
        })
    
    if batch_efficiency < 50:
        recommendations.append({
            "type": "ai_batching",
            "priority": "medium",
            "message": f"AI batch efficiency is {batch_efficiency:.1f}%. Consider optimizing request batching logic."
        })
    
    if avg_response_time > 3.0:
        recommendations.append({
            "type": "response_time",
            "priority": "high",
            "message": f"Average AI response time is {avg_response_time:.2f}s. Consider optimization strategies."
        })
    
    slow_query_count = db_stats.get("slow_queries_count", 0)
    if slow_query_count > 5:
        recommendations.append({
            "type": "database",
            "priority": "medium",
            "message": f"Found {slow_query_count} slow queries. Review database indexes and query optimization."
        })
    
    # Calculate performance score (0-100)
    performance_score = min(100, (
        (cache_hit_rate * 0.3) +
        (batch_efficiency * 0.2) +
        (max(0, 100 - avg_response_time * 10) * 0.3) +
        (max(0, 100 - slow_query_count * 5) * 0.2)
    ))
    
    return {
        "optimization_analysis": {
            "performance_score": round(performance_score, 1),
            "cache_effectiveness": {
                "hit_rate": cache_hit_rate,
                "status": "good" if cache_hit_rate >= 70 else "needs_improvement"
            },
            "ai_efficiency": {
                "batch_efficiency": batch_efficiency,
                "avg_response_time": avg_response_time,
                "status": "good" if batch_efficiency >= 50 and avg_response_time <= 3.0 else "needs_improvement"
            },
            "database_performance": {
                "slow_queries": slow_query_count,
                "avg_query_time": db_stats.get("average_query_time", 0),
                "status": "good" if slow_query_count <= 5 else "needs_improvement"
            }
        },
        "recommendations": recommendations,
        "optimization_wins": [
            "✅ Unified caching system implemented",
            "✅ Database performance indexes added",
            "✅ AI request batching system deployed",
            "✅ Performance monitoring established"
        ]
    }


@router.post("/reset", response_model=Dict[str, str])
def reset_performance_metrics() -> Dict[str, str]:
    """
    Reset all performance metrics (useful for testing and fresh starts).
    
    ⚠️ This will clear all historical performance data.
    """
    monitor = get_performance_monitor()
    monitor.reset_metrics()
    
    return {
        "message": "Performance metrics have been reset",
        "timestamp": datetime.now().isoformat()
    } 