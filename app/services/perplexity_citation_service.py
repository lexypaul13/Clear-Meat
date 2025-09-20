"""Perplexity-based citation service for ingredient analysis."""
import logging
import asyncio
import hashlib
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
from functools import lru_cache
from openai import OpenAI
from app.core.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)


class PerplexityCitationService:
    """Service for generating evidence-based citations using Perplexity API."""
    
    # Trivial ingredients that don't need citations (cost optimization)
    TRIVIAL_INGREDIENTS = frozenset({
        'water', 'salt', 'sugar', 'glucose', 'fructose', 'spices', 'herbs', 'herb',
        'natural flavors', 'natural flavor', 'garlic', 'onion', 'pepper', 'paprika',
        'vinegar', 'lemon juice', 'lime juice', 'citric acid', 'ascorbic acid',
        'beef', 'pork', 'chicken', 'turkey', 'lamb', 'fish', 'salmon', 'tuna',
        'tomatoes', 'tomato paste', 'olive oil', 'sunflower oil', 'vegetable oil',
        'corn starch', 'potato starch', 'wheat flour', 'rice flour', 'yeast',
        'baking soda', 'baking powder', 'vanilla', 'vanilla extract', 'cinnamon',
        'oregano', 'basil', 'thyme', 'rosemary', 'parsley', 'bay leaves'
    })
    
    def __init__(self):
        """Initialize Perplexity citation service."""
        self.api_key = settings.PERPLEXITY_API_KEY
        self.model = settings.PERPLEXITY_MODEL
        
        if not self.api_key:
            logger.warning("Perplexity API key not configured - citations will be empty")
            self.client = None
        else:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.perplexity.ai",
                    timeout=30.0  # Increased from 8s to handle Perplexity's slower response times
                )
                logger.info("Perplexity client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Perplexity client: {e}")
                self.client = None
    
    def should_get_citations(self, ingredient_name: str, risk_level: str) -> bool:
        """Determine if an ingredient needs citations based on risk level and triviality."""
        if risk_level == 'low':
            return False
            
        ingredient_lower = ingredient_name.lower()
        if any(trivial in ingredient_lower for trivial in self.TRIVIAL_INGREDIENTS):
            return False
        
        return risk_level in ['high', 'moderate']
    
    async def get_citations_for_ingredients(
        self, 
        ingredients: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get citations for multiple ingredients in parallel."""
        logger.info(f"Getting citations for {len(ingredients)} ingredients in parallel")
        
        if not self.client:
            logger.warning("Perplexity API client not available")
            return {ingredient: [] for ingredient in ingredients}
        
        # Execute API calls with rate limiting to avoid 429 errors
        # Process in smaller batches with delays between batches
        batch_size = 3  # Reduced from unlimited parallel to 3 concurrent requests
        results = []
        
        for i in range(0, len(ingredients), batch_size):
            batch = ingredients[i:i + batch_size]
            tasks = [self._get_citations_for_ingredient(ingredient) for ingredient in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # Add delay between batches to respect rate limits
            if i + batch_size < len(ingredients):
                await asyncio.sleep(1.0)  # 1 second delay between batches
        
        # Build citations map from parallel results
        citations_map = {}
        for ingredient, result in zip(ingredients, results):
            if isinstance(result, Exception):
                logger.error(f"Error getting citations for {ingredient}: {result}")
                citations_map[ingredient] = []
            else:
                citations_map[ingredient] = result
        
        return citations_map
    
    async def _get_citations_for_ingredient(self, ingredient_name: str) -> List[Dict[str, Any]]:
        """Get citations for a single ingredient from Perplexity API with caching."""
        # Check cache first (24h TTL for ingredient citations)
        cache_key = self._generate_cache_key(ingredient_name)
        cached_citations = cache.get(cache_key)
        if cached_citations:
            logger.info(f"[Citation Cache] Using cached citations for: {ingredient_name}")
            return cached_citations
        
        query = f"Medical research on {ingredient_name} health effects and safety in food. Provide peer-reviewed studies and health authority reports."
        logger.info(f"[Citation Research] Researching: {ingredient_name}")
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a medical research expert. Provide accurate information about food ingredient health effects."},
                        {"role": "user", "content": query}
                    ],
                    max_tokens=1000,
                    temperature=0.1
                )
            )
            
            citations = self._extract_citations_from_response(response)
            
            # Cache successful results for 24 hours
            if citations:
                cache.set(cache_key, citations, ttl=86400)
                logger.info(f"[Citation Cache] Cached {len(citations)} citations for: {ingredient_name}")
            
            return citations
            
        except Exception as e:
            logger.error(f"[Citation Research] API error for {ingredient_name}: {e}")
            return []
    
    def _generate_cache_key(self, ingredient_name: str) -> str:
        """Generate cache key for ingredient citations."""
        ingredient_hash = hashlib.md5(ingredient_name.lower().encode()).hexdigest()[:12]
        return f"perplexity_citations_{ingredient_hash}"
    
    def _extract_citations_from_response(self, response) -> List[Dict[str, Any]]:
        """Extract citations from Perplexity response."""
        citations = []
        
        try:
            # Perplexity returns citations as an array of URLs
            if hasattr(response, 'citations') and response.citations:
                logger.info(f"Found {len(response.citations)} citations from Perplexity")
                
                for i, citation_url in enumerate(response.citations[:3], 1):
                    citation_data = {
                        "id": i,
                        "title": self._extract_title_from_url(citation_url),
                        "source": self._extract_source_from_url(citation_url),
                        "year": 2024,
                        "url": citation_url
                    }
                    citations.append(citation_data)
                    logger.info(f"Processed citation {i}: {citation_data['title'][:50]}...")
            
        except Exception as e:
            logger.error(f"Error extracting citations: {e}")
        
        return citations[:3]
    
    @lru_cache(maxsize=128)
    def _get_domain_info(self, url: str) -> Tuple[str, str]:
        """Get title and source info for a URL with caching."""
        try:
            url_lower = url.lower()
            domain = urlparse(url).netloc.replace('www.', '')
            
            # Domain mapping for consistent results
            domain_map = {
                'pubmed': ("PubMed Medical Research Study", "PubMed/NCBI"),
                'ncbi.nlm.nih.gov': ("PubMed Medical Research Study", "PubMed/NCBI"),
                'nature.com': ("Nature Scientific Publication", "Nature Publishing"),
                'fda.gov': ("FDA Official Report", "U.S. Food and Drug Administration"),
                'who.int': ("WHO Health Guidelines", "World Health Organization"),
                'nih.gov': ("NIH Research Publication", "National Institutes of Health"),
                'sciencedirect.com': ("ScienceDirect Research Article", "ScienceDirect")
            }
            
            for domain_key, (title, source) in domain_map.items():
                if domain_key in url_lower:
                    return title, source
            
            # Default case
            return f"Research study from {domain}", domain
            
        except Exception:
            return "Scientific Research Publication", "Scientific Database"
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a meaningful title from a URL."""
        title, _ = self._get_domain_info(url)
        return title
    
    def _extract_source_from_url(self, url: str) -> str:
        """Extract source information from URL."""
        _, source = self._get_domain_info(url)
        return source


# Singleton instance for performance
_citation_service_instance = None

def get_citation_service() -> PerplexityCitationService:
    """Get singleton instance of PerplexityCitationService."""
    global _citation_service_instance
    if _citation_service_instance is None:
        _citation_service_instance = PerplexityCitationService()
    return _citation_service_instance


# Integration function for existing product assessment system
async def integrate_perplexity_citations(assessment_result: Dict[str, Any]) -> Dict[str, Any]:
    """Add Perplexity citations to existing Gemini assessment."""
    logger.info("Integrating Perplexity citations with Gemini assessment")
    
    # Extract high-risk AND moderate-risk ingredients from assessment
    ingredients_assessment = assessment_result.get("ingredients_assessment", {})
    target_ingredients = []
    
    for ingredient in ingredients_assessment.get("high_risk", []):
        if isinstance(ingredient, dict) and "name" in ingredient:
            target_ingredients.append(ingredient["name"])
    
    for ingredient in ingredients_assessment.get("moderate_risk", []):
        if isinstance(ingredient, dict) and "name" in ingredient:
            target_ingredients.append(ingredient["name"])
    
    if not target_ingredients:
        logger.info("No high/moderate-risk ingredients found")
        return assessment_result
    
    # Use singleton citation service
    citation_service = get_citation_service()
    
    # Filter ingredients that need citations
    filtered_ingredients = [
        ing for ing in target_ingredients 
        if citation_service.should_get_citations(ing, "moderate")  # This checks both high and moderate
    ]
    
    if not filtered_ingredients:
        logger.info("No ingredients need citations after filtering")
        return assessment_result
    
    logger.info(f"Getting citations for {len(filtered_ingredients)} ingredients")
    
    # Get citations
    citations_map = await citation_service.get_citations_for_ingredients(filtered_ingredients)
    
    # Add citations to ingredients
    for category in ["high_risk", "moderate_risk"]:
        for ingredient in ingredients_assessment.get(category, []):
            ingredient_name = ingredient.get("name", "")
            if ingredient_name in citations_map:
                ingredient["citations"] = [cite["id"] for cite in citations_map[ingredient_name]]
    
    # Flatten citations for response with optimized ID assignment
    all_citations = [
        {**citation, "id": i}
        for i, citation in enumerate(
            (cite for ingredient_citations in citations_map.values() 
             for cite in ingredient_citations), 
            1
        )
    ]
    
    assessment_result["citations"] = all_citations
    logger.info(f"Added {len(all_citations)} citations to assessment")
    
    return assessment_result