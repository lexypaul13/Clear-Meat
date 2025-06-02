"""AI Batch Processing Service for optimizing Gemini API calls."""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, NamedTuple
from dataclasses import dataclass
from enum import Enum
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading

import google.generativeai as genai
from app.core.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)


class RequestType(Enum):
    """Types of AI requests that can be batched."""
    SEARCH_INTENT = "search_intent"
    HEALTH_ASSESSMENT = "health_assessment"
    RECOMMENDATIONS = "recommendations"


@dataclass
class AIRequest:
    """Represents a single AI request."""
    id: str
    request_type: RequestType
    prompt: str
    priority: int = 5  # 1 = highest, 10 = lowest
    timeout: float = 30.0
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class AIResponse:
    """Represents the response to an AI request."""
    request_id: str
    success: bool
    data: Any = None
    error: str = None
    processing_time: float = 0.0


class AIBatchProcessor:
    """Batches and processes AI requests efficiently."""
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 2.0, max_workers: int = 3):
        """
        Initialize the batch processor.
        
        Args:
            batch_size: Maximum number of requests to batch together
            batch_timeout: Maximum time to wait before processing a partial batch
            max_workers: Maximum number of concurrent processing threads
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_workers = max_workers
        
        # Request queues by type
        self.queues: Dict[RequestType, List[AIRequest]] = {
            req_type: [] for req_type in RequestType
        }
        
        # Response tracking
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Processing state
        self.processing_lock = threading.Lock()
        self.shutdown_event = threading.Event()
        
        # Thread pool for processing
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Start background processing
        self.processing_thread = threading.Thread(target=self._process_batches_loop, daemon=True)
        self.processing_thread.start()
        
        logger.info(f"AI Batch Processor initialized: batch_size={batch_size}, timeout={batch_timeout}s")
    
    async def submit_request(self, request: AIRequest) -> AIResponse:
        """
        Submit an AI request for batch processing.
        
        Args:
            request: The AI request to process
            
        Returns:
            The AI response
        """
        # Check cache first
        cache_key = cache.generate_key(
            request.request_type.value, 
            request.prompt[:100],  # Use first 100 chars for caching
            prefix="ai_batch"
        )
        
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for request {request.id}")
            return AIResponse(
                request_id=request.id,
                success=True,
                data=cached_result,
                processing_time=0.0
            )
        
        # Create future for response
        future = asyncio.Future()
        self.pending_responses[request.id] = future
        
        # Add to appropriate queue
        with self.processing_lock:
            self.queues[request.request_type].append(request)
            logger.debug(f"Queued request {request.id} (type: {request.request_type.value})")
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=request.timeout)
            
            # Cache successful responses
            if response.success and response.data:
                ttl = self._get_cache_ttl(request.request_type)
                cache.set(cache_key, response.data, ttl=ttl)
            
            return response
            
        except asyncio.TimeoutError:
            # Clean up on timeout
            self.pending_responses.pop(request.id, None)
            return AIResponse(
                request_id=request.id,
                success=False,
                error="Request timeout"
            )
    
    def _process_batches_loop(self):
        """Background thread that processes batches continuously."""
        logger.info("Started AI batch processing loop")
        
        while not self.shutdown_event.is_set():
            try:
                self._process_ready_batches()
                time.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                logger.error(f"Error in batch processing loop: {e}")
                time.sleep(1.0)  # Longer delay on error
    
    def _process_ready_batches(self):
        """Process batches that are ready (full or timed out)."""
        current_time = time.time()
        
        for request_type in RequestType:
            with self.processing_lock:
                queue = self.queues[request_type]
                
                if not queue:
                    continue
                
                # Check if batch is ready
                oldest_request_age = current_time - queue[0].created_at
                should_process = (
                    len(queue) >= self.batch_size or
                    oldest_request_age >= self.batch_timeout
                )
                
                if should_process:
                    # Extract batch for processing
                    batch = queue[:self.batch_size]
                    self.queues[request_type] = queue[self.batch_size:]
                    
                    # Submit batch for async processing
                    self.executor.submit(self._process_batch, request_type, batch)
    
    def _process_batch(self, request_type: RequestType, batch: List[AIRequest]):
        """Process a batch of requests of the same type."""
        start_time = time.time()
        logger.info(f"Processing batch of {len(batch)} {request_type.value} requests")
        
        try:
            if request_type == RequestType.SEARCH_INTENT:
                results = self._process_search_intent_batch(batch)
            elif request_type == RequestType.HEALTH_ASSESSMENT:
                results = self._process_health_assessment_batch(batch)
            elif request_type == RequestType.RECOMMENDATIONS:
                results = self._process_recommendations_batch(batch)
            else:
                # Fallback: process individually
                results = self._process_individual_requests(batch)
            
            # Send responses
            processing_time = time.time() - start_time
            for request, result in zip(batch, results):
                response = AIResponse(
                    request_id=request.id,
                    success=result is not None,
                    data=result,
                    error=None if result is not None else "Processing failed",
                    processing_time=processing_time / len(batch)
                )
                
                # Notify waiting coroutine
                future = self.pending_responses.pop(request.id, None)
                if future and not future.done():
                    try:
                        future.set_result(response)
                    except Exception as e:
                        logger.error(f"Error setting future result: {e}")
            
            logger.info(f"Completed batch processing in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            
            # Send error responses
            for request in batch:
                response = AIResponse(
                    request_id=request.id,
                    success=False,
                    error=str(e)
                )
                
                future = self.pending_responses.pop(request.id, None)
                if future and not future.done():
                    try:
                        future.set_result(response)
                    except Exception as e2:
                        logger.error(f"Error setting error result: {e2}")
    
    def _process_search_intent_batch(self, batch: List[AIRequest]) -> List[Any]:
        """Process a batch of search intent requests."""
        # Combine multiple queries into a single prompt
        combined_prompt = self._build_combined_search_prompt(batch)
        
        try:
            model = genai.GenerativeModel(settings.GEMINI_MODEL or 'gemini-2.0-flash')
            response = model.generate_content(combined_prompt)
            
            # Parse the batch response
            return self._parse_batch_search_response(response.text, len(batch))
            
        except Exception as e:
            logger.error(f"Error in batch search intent processing: {e}")
            return [None] * len(batch)
    
    def _process_health_assessment_batch(self, batch: List[AIRequest]) -> List[Any]:
        """Process a batch of health assessment requests."""
        # For health assessments, process individually for now
        # (could be optimized further with product comparison prompts)
        return self._process_individual_requests(batch)
    
    def _process_recommendations_batch(self, batch: List[AIRequest]) -> List[Any]:
        """Process a batch of recommendation requests."""
        # Recommendations can sometimes be batched by user preferences
        if self._can_batch_recommendations(batch):
            return self._process_combined_recommendations(batch)
        else:
            return self._process_individual_requests(batch)
    
    def _process_individual_requests(self, batch: List[AIRequest]) -> List[Any]:
        """Process requests individually (fallback method)."""
        results = []
        
        for request in batch:
            try:
                model = genai.GenerativeModel(settings.GEMINI_MODEL or 'gemini-2.0-flash')
                response = model.generate_content(request.prompt)
                
                # Parse based on request type
                if request.request_type == RequestType.SEARCH_INTENT:
                    result = self._parse_search_intent_response(response.text)
                elif request.request_type == RequestType.HEALTH_ASSESSMENT:
                    result = self._parse_health_assessment_response(response.text)
                elif request.request_type == RequestType.RECOMMENDATIONS:
                    result = self._parse_recommendations_response(response.text)
                else:
                    result = response.text
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing individual request {request.id}: {e}")
                results.append(None)
        
        return results
    
    def _build_combined_search_prompt(self, batch: List[AIRequest]) -> str:
        """Build a combined prompt for multiple search queries."""
        queries = []
        for i, request in enumerate(batch):
            # Extract query from prompt (assuming it's in specific format)
            query_start = request.prompt.find('Query: "') + 8
            query_end = request.prompt.find('"', query_start)
            if query_start > 7 and query_end > query_start:
                query = request.prompt[query_start:query_end]
                queries.append(f"{i+1}. {query}")
        
        combined_prompt = f"""Parse these {len(queries)} natural language search queries for meat products. 
For each query, extract structured search criteria and respond with a JSON array containing the results.

Queries:
{chr(10).join(queries)}

For each query, extract:
1. Meat types (beef, chicken, turkey, pork, lamb, etc.)
2. Nutritional constraints with values
3. Health preferences: organic, grass-fed, antibiotic-free, etc.
4. Product types: jerky, snacks, breast, patties, etc.
5. Ingredients to exclude
6. Risk preference
7. Keywords

Respond with JSON array in this format:
[
  {{
    "query_index": 1,
    "meat_types": ["chicken"],
    "nutritional_constraints": {{"max_salt": 1.0}},
    "health_preferences": ["organic"],
    "product_types": ["snacks"],
    "exclude_ingredients": ["preservatives"],
    "risk_preference": "Green",
    "keywords": ["healthy"]
  }},
  ...
]"""
        
        return combined_prompt
    
    def _parse_batch_search_response(self, response_text: str, expected_count: int) -> List[Any]:
        """Parse batch search response into individual results."""
        try:
            # Clean up response
            text = response_text.strip()
            if text.startswith("```json") and text.endswith("```"):
                text = text[7:-3].strip()
            
            results = json.loads(text)
            
            # Ensure we have the right number of results
            if len(results) != expected_count:
                logger.warning(f"Expected {expected_count} results, got {len(results)}")
                # Pad with None or truncate as needed
                while len(results) < expected_count:
                    results.append(None)
                results = results[:expected_count]
            
            return results
            
        except Exception as e:
            logger.error(f"Error parsing batch search response: {e}")
            return [None] * expected_count
    
    def _parse_search_intent_response(self, response_text: str) -> Any:
        """Parse individual search intent response."""
        try:
            text = response_text.strip()
            if text.startswith("```json") and text.endswith("```"):
                text = text[7:-3].strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error parsing search intent response: {e}")
            return None
    
    def _parse_health_assessment_response(self, response_text: str) -> Any:
        """Parse health assessment response."""
        try:
            text = response_text.strip()
            if text.startswith("```json") and text.endswith("```"):
                text = text[7:-3].strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error parsing health assessment response: {e}")
            return None
    
    def _parse_recommendations_response(self, response_text: str) -> Any:
        """Parse recommendations response."""
        try:
            text = response_text.strip()
            if text.startswith("```json") and text.endswith("```"):
                text = text[7:-3].strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Error parsing recommendations response: {e}")
            return None
    
    def _can_batch_recommendations(self, batch: List[AIRequest]) -> bool:
        """Check if recommendation requests can be batched."""
        # For now, don't batch recommendations (each has unique user context)
        return False
    
    def _process_combined_recommendations(self, batch: List[AIRequest]) -> List[Any]:
        """Process combined recommendation requests."""
        # Placeholder for future implementation
        return self._process_individual_requests(batch)
    
    def _get_cache_ttl(self, request_type: RequestType) -> int:
        """Get cache TTL based on request type."""
        if request_type == RequestType.SEARCH_INTENT:
            return 7200  # 2 hours
        elif request_type == RequestType.HEALTH_ASSESSMENT:
            return 86400  # 24 hours
        elif request_type == RequestType.RECOMMENDATIONS:
            return 3600  # 1 hour
        return 3600  # Default 1 hour
    
    def shutdown(self):
        """Shutdown the batch processor."""
        logger.info("Shutting down AI batch processor")
        self.shutdown_event.set()
        self.executor.shutdown(wait=True)
        
        # Cancel any pending futures
        for future in self.pending_responses.values():
            if not future.done():
                future.cancel()


# Global batch processor instance
_batch_processor: Optional[AIBatchProcessor] = None


def get_batch_processor() -> AIBatchProcessor:
    """Get or create the global batch processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = AIBatchProcessor(
            batch_size=3,  # Smaller batches for responsiveness
            batch_timeout=1.5,  # Quick processing
            max_workers=2  # Conservative threading
        )
    return _batch_processor


async def batch_process_request(
    request_type: RequestType,
    prompt: str,
    priority: int = 5,
    timeout: float = 30.0
) -> Optional[Any]:
    """
    Convenience function to submit a request for batch processing.
    
    Args:
        request_type: Type of AI request
        prompt: The prompt to send to the AI
        priority: Request priority (1=highest, 10=lowest)
        timeout: Request timeout in seconds
        
    Returns:
        The AI response data or None if failed
    """
    processor = get_batch_processor()
    
    request = AIRequest(
        id=str(uuid.uuid4()),
        request_type=request_type,
        prompt=prompt,
        priority=priority,
        timeout=timeout
    )
    
    response = await processor.submit_request(request)
    
    if response.success:
        return response.data
    else:
        logger.error(f"Batch request failed: {response.error}")
        return None 