"""
NLP Search Service using Google Gemini for intelligent product search.

This service provides natural language understanding for product searches,
converting user queries into structured database filters.
"""

import json
import logging
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)

class NLPSearchService:
    def __init__(self):
        """Initialize the NLP search service with Gemini AI."""
        self.model = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of Gemini AI service."""
        if self._initialized:
            return
        
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for NLP search")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        self._initialized = True
    
    async def parse_search_query(self, query: str) -> Dict[str, Any]:
        """
        Parse a natural language search query into structured search parameters.
        
        Args:
            query: Natural language search query
            
        Returns:
            Dict containing parsed search parameters
        """
        try:
            # Try to initialize Gemini service
            self._ensure_initialized()
            
            prompt = self._build_parsing_prompt(query)
            response = await self._call_gemini(prompt)
            return self._parse_gemini_response(response)
        
        except ValueError as ve:
            if "GEMINI_API_KEY" in str(ve):
                logger.warning(f"Gemini API key not configured: {ve}")
                # Return fallback parsing without AI
                return self._fallback_parse_query(query)
            else:
                raise ve
        
        except Exception as e:
            logger.error(f"Error parsing search query '{query}': {e}")
            # Fallback to basic text search
            return self._fallback_parse_query(query)
    
    def _fallback_parse_query(self, query: str) -> Dict[str, Any]:
        """Fallback query parsing without AI."""
        return {
            "keywords": [query.lower()],
            "meat_types": [],
            "nutrition_filters": {},
            "quality_preferences": [],
            "health_intent": "balanced",
            "confidence": 0.1
        }
    
    def _build_parsing_prompt(self, query: str) -> str:
        """Build the prompt for Gemini to parse the search query."""
        return f"""
You are a food search assistant. Parse this natural language query into structured search parameters.

Query: "{query}"

Extract and return ONLY a valid JSON object with these fields:

{{
  "meat_types": [],
  "nutrition_filters": {{}},
  "quality_preferences": [],
  "health_intent": "string",
  "keywords": [],
  "confidence": float
}}

Field definitions:
- meat_types: Array of ["chicken", "beef", "pork", "turkey", "fish", "lamb"] if mentioned
- nutrition_filters: Object with max/min nutrition values like {{"max_sodium": 500, "min_protein": 20}}
- quality_preferences: Array of ["organic", "grass-fed", "antibiotic-free", "no-preservatives", "natural"] 
- health_intent: One of ["healthy", "indulgent", "balanced", "clean"]
- keywords: Array of remaining important words not captured above
- confidence: Float 0-1 indicating how well you understood the query

Examples:
"healthy chicken options" → {{"meat_types": ["chicken"], "health_intent": "healthy", "keywords": [], "confidence": 0.9}}
"low sodium beef for dinner" → {{"meat_types": ["beef"], "nutrition_filters": {{"max_sodium": 500}}, "keywords": ["dinner"], "confidence": 0.8}}
"organic grass-fed options" → {{"quality_preferences": ["organic", "grass-fed"], "health_intent": "clean", "keywords": [], "confidence": 0.9}}
"something tasty" → {{"health_intent": "indulgent", "keywords": ["tasty"], "confidence": 0.6}}

Return ONLY the JSON, no explanation.
"""

    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API with the parsing prompt."""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    def _parse_gemini_response(self, response: str) -> Dict[str, Any]:
        """Parse Gemini's JSON response into structured data."""
        try:
            # Clean up response to extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            
            parsed = json.loads(response)
            
            # Validate and clean the response
            return {
                "meat_types": parsed.get("meat_types", []),
                "nutrition_filters": parsed.get("nutrition_filters", {}),
                "quality_preferences": parsed.get("quality_preferences", []),
                "health_intent": parsed.get("health_intent", "balanced"),
                "keywords": parsed.get("keywords", []),
                "confidence": min(max(parsed.get("confidence", 0.5), 0.0), 1.0)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Raw response: {response}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
    
    def build_database_query(self, parsed_query: Dict[str, Any], supabase_client) -> Any:
        """
        Build a Supabase query from parsed search parameters.
        
        Args:
            parsed_query: Parsed search parameters from parse_search_query
            supabase_client: Supabase client instance
            
        Returns:
            Supabase query object
        """
        query = supabase_client.table('products').select('*')
        
        # Filter by meat types
        if parsed_query.get("meat_types"):
            query = query.in_('meat_type', parsed_query["meat_types"])
        
        # Apply nutrition filters
        nutrition_filters = parsed_query.get("nutrition_filters", {})
        if "max_sodium" in nutrition_filters:
            query = query.lte('salt', nutrition_filters["max_sodium"] / 1000)  # Convert mg to g
        if "min_protein" in nutrition_filters:
            query = query.gte('protein', nutrition_filters["min_protein"])
        if "max_fat" in nutrition_filters:
            query = query.lte('fat', nutrition_filters["max_fat"])
        if "max_calories" in nutrition_filters:
            query = query.lte('calories', nutrition_filters["max_calories"])
        
        # Filter by health intent
        health_intent = parsed_query.get("health_intent", "balanced")
        if health_intent == "healthy":
            # Prefer products with green/yellow risk ratings
            query = query.in_('risk_rating', ['Green', 'Yellow'])
        elif health_intent == "clean":
            # Prefer products with green risk rating
            query = query.eq('risk_rating', 'Green')
        
        # Apply quality preferences through ingredient text search
        quality_prefs = parsed_query.get("quality_preferences", [])
        if quality_prefs:
            quality_conditions = []
            for pref in quality_prefs:
                quality_conditions.append(f'ingredients_text.ilike."%{pref}%"')
            if quality_conditions:
                query = query.or_(','.join(quality_conditions))
        
        # Apply keyword search on remaining terms
        keywords = parsed_query.get("keywords", [])
        if keywords:
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.extend([
                    f'name.ilike."%{keyword}%"',
                    f'ingredients_text.ilike."%{keyword}%"',
                    f'brand.ilike."%{keyword}%"'
                ])
            if keyword_conditions:
                query = query.or_(','.join(keyword_conditions))
        
        return query
    
    def rank_results(self, results: List[Dict[str, Any]], parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Rank and score search results based on relevance to the parsed query.
        
        Args:
            results: List of product dictionaries from database
            parsed_query: Parsed search parameters
            
        Returns:
            Sorted list of products with relevance scores
        """
        if not results:
            return results
        
        scored_results = []
        
        for product in results:
            score = self._calculate_relevance_score(product, parsed_query)
            product_with_score = product.copy()
            product_with_score['_relevance_score'] = score
            scored_results.append(product_with_score)
        
        # Sort by relevance score (highest first)
        scored_results.sort(key=lambda x: x['_relevance_score'], reverse=True)
        
        return scored_results
    
    def _calculate_relevance_score(self, product: Dict[str, Any], parsed_query: Dict[str, Any]) -> float:
        """Calculate relevance score for a product based on the search query."""
        score = 0.0
        
        # Base score for all products
        score += 0.1
        
        # Meat type match (high weight)
        if parsed_query.get("meat_types") and product.get("meat_type") in parsed_query["meat_types"]:
            score += 0.4
        
        # Health intent scoring
        health_intent = parsed_query.get("health_intent", "balanced")
        risk_rating = product.get("risk_rating", "").lower()
        
        if health_intent == "healthy" and risk_rating == "green":
            score += 0.3
        elif health_intent == "healthy" and risk_rating == "yellow":
            score += 0.2
        elif health_intent == "clean" and risk_rating == "green":
            score += 0.4
        elif health_intent == "indulgent" and risk_rating in ["orange", "red"]:
            score += 0.2
        
        # Nutrition filters scoring
        nutrition_filters = parsed_query.get("nutrition_filters", {})
        if "max_sodium" in nutrition_filters and product.get("salt"):
            if product["salt"] * 1000 <= nutrition_filters["max_sodium"]:  # Convert g to mg
                score += 0.2
        
        if "min_protein" in nutrition_filters and product.get("protein"):
            if product["protein"] >= nutrition_filters["min_protein"]:
                score += 0.2
        
        # Quality preferences scoring
        quality_prefs = parsed_query.get("quality_preferences", [])
        ingredients_text = product.get("ingredients_text", "").lower()
        for pref in quality_prefs:
            if pref.lower() in ingredients_text:
                score += 0.15
        
        # Keyword match scoring
        keywords = parsed_query.get("keywords", [])
        product_text = f"{product.get('name', '')} {product.get('brand', '')} {ingredients_text}".lower()
        for keyword in keywords:
            if keyword.lower() in product_text:
                score += 0.1
        
        # Confidence factor
        confidence = parsed_query.get("confidence", 0.5)
        score *= (0.5 + 0.5 * confidence)  # Scale score by confidence
        
        return min(score, 1.0)  # Cap at 1.0


# Global instance - lazy initialization
_nlp_search_service = None

def get_nlp_search_service() -> NLPSearchService:
    """Dependency to get NLP search service."""
    global _nlp_search_service
    if _nlp_search_service is None:
        _nlp_search_service = NLPSearchService()
    return _nlp_search_service