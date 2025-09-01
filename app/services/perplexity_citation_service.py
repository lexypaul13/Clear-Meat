"""Perplexity-based citation service for ingredient analysis."""
import logging
import asyncio
from typing import List, Dict, Any
from urllib.parse import urlparse
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class PerplexityCitationService:
    """Service for generating evidence-based citations using Perplexity API."""
    
    # Trivial ingredients that don't need citations (cost optimization)
    TRIVIAL_INGREDIENTS = {
        'water', 'salt', 'sugar', 'glucose', 'fructose', 'spices', 'herbs', 'herb',
        'natural flavors', 'natural flavor', 'garlic', 'onion', 'pepper', 'paprika',
        'vinegar', 'lemon juice', 'lime juice', 'citric acid', 'ascorbic acid',
        'beef', 'pork', 'chicken', 'turkey', 'lamb', 'fish', 'salmon', 'tuna',
        'tomatoes', 'tomato paste', 'olive oil', 'sunflower oil', 'vegetable oil',
        'corn starch', 'potato starch', 'wheat flour', 'rice flour', 'yeast',
        'baking soda', 'baking powder', 'vanilla', 'vanilla extract', 'cinnamon',
        'oregano', 'basil', 'thyme', 'rosemary', 'parsley', 'bay leaves'
    }
    
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
                    timeout=30.0
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
        """Get citations for multiple ingredients."""
        logger.info(f"Getting citations for {len(ingredients)} ingredients")
        
        if not self.client:
            logger.warning("Perplexity API client not available")
            return {ingredient: [] for ingredient in ingredients}
        
        citations_map = {}
        for ingredient in ingredients:
            try:
                citations = await self._get_citations_for_ingredient(ingredient)
                citations_map[ingredient] = citations
            except Exception as e:
                logger.error(f"Error getting citations for {ingredient}: {e}")
                citations_map[ingredient] = []
        
        return citations_map
    
    async def _get_citations_for_ingredient(self, ingredient_name: str) -> List[Dict[str, Any]]:
        """Get citations for a single ingredient from Perplexity API."""
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
            
            return self._extract_citations_from_response(response)
            
        except Exception as e:
            logger.error(f"[Citation Research] API error for {ingredient_name}: {e}")
            return []
    
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
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a meaningful title from a URL."""
        try:
            if 'pubmed' in url.lower() or 'ncbi.nlm.nih.gov' in url.lower():
                return "PubMed Medical Research Study"
            elif 'nature.com' in url.lower():
                return "Nature Scientific Publication"
            elif 'fda.gov' in url.lower():
                return "FDA Official Report"
            elif 'who.int' in url.lower():
                return "WHO Health Guidelines"
            elif 'nih.gov' in url.lower():
                return "NIH Research Publication"
            elif 'sciencedirect.com' in url.lower():
                return "ScienceDirect Research Article"
            else:
                domain = urlparse(url).netloc.replace('www.', '')
                return f"Research study from {domain}"
        except:
            return "Scientific Research Publication"
    
    def _extract_source_from_url(self, url: str) -> str:
        """Extract source information from URL."""
        try:
            if 'pubmed' in url.lower() or 'ncbi.nlm.nih.gov' in url.lower():
                return "PubMed/NCBI"
            elif 'nature.com' in url.lower():
                return "Nature Publishing"
            elif 'fda.gov' in url.lower():
                return "U.S. Food and Drug Administration"
            elif 'who.int' in url.lower():
                return "World Health Organization"
            elif 'nih.gov' in url.lower():
                return "National Institutes of Health"
            elif 'sciencedirect.com' in url.lower():
                return "ScienceDirect"
            else:
                domain = urlparse(url).netloc.replace('www.', '')
                return domain
        except:
            return "Scientific Database"


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
    
    # Initialize citation service and get citations
    citation_service = PerplexityCitationService()
    
    # Filter ingredients that need citations
    filtered_ingredients = [
        ing for ing in target_ingredients 
        if citation_service.should_get_citations(ing, "high")
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
    
    # Flatten citations for response
    all_citations = []
    citation_id = 1
    for ingredient_citations in citations_map.values():
        for citation in ingredient_citations:
            citation["id"] = citation_id
            all_citations.append(citation)
            citation_id += 1
    
    assessment_result["citations"] = all_citations
    logger.info(f"Added {len(all_citations)} citations to assessment")
    
    return assessment_result