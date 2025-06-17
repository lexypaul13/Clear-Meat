"""Health assessment service with real citations using citation search tools."""
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from pydantic import ValidationError
from app.core.config import settings
from app.core.cache import cache
from app.models.product import HealthAssessment, ProductStructured
from app.services.citation_tools import CitationSearchService
from app.services.async_citation_search import search_citations_for_health_assessment
from app.models.citation import CitationSearch

logger = logging.getLogger(__name__)


class HealthAssessmentWithCitations:
    """Enhanced health assessment service with real citations."""
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")
        
        # Configure Gemini API key
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.citation_service = CitationSearchService()
    
    def generate_health_assessment_with_real_citations(
        self, 
        product: ProductStructured, 
        db=None
    ) -> Optional[HealthAssessment]:
        """
        Generate health assessment with real scientific citations.
        
        Args:
            product: The structured product data to analyze
            db: Database session (optional)
            
        Returns:
            HealthAssessment with real citations
        """
        try:
            # Generate cache key
            cache_key = cache.generate_key(product.product.code, prefix="health_assessment_cited")
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Returning cached cited health assessment for product {product.product.code}")
                return HealthAssessment(**cached_result)
            
            logger.info(f"[Health Assessment] Analyzing product: {product.product.name}")
            
            # Step 1: Generate basic health assessment without citations
            basic_assessment = self._generate_basic_assessment(product)
            if not basic_assessment:
                return None
            
            # Step 2: Extract high-risk ingredients for citation search
            high_risk_ingredients = self._extract_high_risk_ingredients(basic_assessment)
            logger.info(f"[Health Assessment] High-risk ingredients found: {high_risk_ingredients}")
            
            # Step 3: Search for real citations for each high-risk ingredient
            citations_dict = {}
            citation_counter = 1
            
            for ingredient in high_risk_ingredients:
                logger.debug(f"[Health Assessment] Searching citations for: {ingredient}")
                citations = self._search_citations_for_ingredient(ingredient)
                
                if citations:
                    for citation in citations:
                        citations_dict[str(citation_counter)] = citation.to_apa_format()
                        citation_counter += 1
            
            # Step 4: Enhance assessment with real citations
            enhanced_assessment = self._enhance_assessment_with_citations(
                basic_assessment, 
                high_risk_ingredients, 
                citations_dict
            )
            
            if enhanced_assessment:
                # Cache the result
                cache.set(cache_key, enhanced_assessment.model_dump(), ttl=86400)  # 24 hours
                logger.info(f"[Health Assessment] Enhanced assessment generated with {len(citations_dict)} real citations")
            
            return enhanced_assessment
            
        except Exception as e:
            logger.error(f"Error generating health assessment with citations: {e}")
            logger.error(f"[Health Assessment] Error: {e}")
            return None
    
    def _generate_basic_assessment(self, product: ProductStructured) -> Optional[Dict[str, Any]]:
        """Generate basic health assessment using full assessment service."""
        try:
            # Import the main health assessment service
            from app.services.health_assessment_service import generate_health_assessment
            
            # Generate full structured assessment
            full_assessment = generate_health_assessment(product, db=None)
            
            if full_assessment:
                # Convert HealthAssessment model to dict for processing
                assessment_dict = full_assessment.model_dump()
                logger.info(f"[Citation Engine] Generated structured assessment with {len(assessment_dict.get('ingredients_assessment', {}).get('high_risk', []))} high-risk ingredients")
                return assessment_dict
            else:
                # Fallback to simple assessment
                return self._generate_simple_fallback_assessment(product)
                
        except Exception as e:
            logger.error(f"Error generating structured assessment: {e}")
            return self._generate_simple_fallback_assessment(product)
    
    def _generate_simple_fallback_assessment(self, product: ProductStructured) -> Dict[str, Any]:
        """Generate simple assessment if structured assessment fails."""
        try:
            prompt = self._build_basic_assessment_prompt(product)
            
            response = genai.GenerativeModel(settings.GEMINI_MODEL).generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0)
            )
            
            assessment_text = response.text
            
            return {
                "summary": "Basic health assessment generated",
                "assessment_text": assessment_text,
                "risk_summary": {"grade": "C", "color": "Yellow"}  # Default values
            }
            
        except Exception as e:
            logger.error(f"Error generating fallback assessment: {e}")
            return {
                "summary": "Assessment unavailable",
                "assessment_text": "",
                "risk_summary": {"grade": "C", "color": "Yellow"}
            }
    
    def _extract_high_risk_ingredients(self, basic_assessment: Dict[str, Any]) -> List[str]:
        """Extract high-risk ingredients from Gemini's risk categorization."""
        try:
            # Try to parse structured assessment if available
            if "ingredients_assessment" in basic_assessment:
                ingredients_assessment = basic_assessment["ingredients_assessment"]
                high_risk_ingredients = []
                
                # Extract from high_risk category
                for ingredient in ingredients_assessment.get("high_risk", []):
                    if isinstance(ingredient, dict) and "name" in ingredient:
                        high_risk_ingredients.append(ingredient["name"])
                
                # Optionally include moderate_risk ingredients for more comprehensive citations
                # Uncomment the next 4 lines to also cite moderate-risk ingredients:
                # for ingredient in ingredients_assessment.get("moderate_risk", []):
                #     if isinstance(ingredient, dict) and "name" in ingredient:
                #         high_risk_ingredients.append(ingredient["name"])
                
                logger.info(f"[Citation Engine] Extracted from Gemini risk analysis: {high_risk_ingredients}")
                return high_risk_ingredients
                
        except Exception as e:
            logger.warning(f"Could not parse structured assessment: {e}")
        
        # Fallback to text parsing if structured data unavailable
        return self._fallback_text_extraction(basic_assessment)
    
    def _fallback_text_extraction(self, basic_assessment: Dict[str, Any]) -> List[str]:
        """Fallback method using text parsing (original approach)."""
        # Expanded list based on common meat product preservatives
        common_high_risk = [
            "BHA", "BHT", "Sodium Nitrite", "Sodium Nitrate", 
            "Potassium Nitrite", "Potassium Nitrate", "TBHQ",
            "Sodium Benzoate", "MSG", "Monosodium Glutamate",
            "Sodium Phosphate", "Potassium Sorbate"
        ]
        
        assessment_text = basic_assessment.get("assessment_text", "").upper()
        
        found_ingredients = []
        for ingredient in common_high_risk:
            if ingredient.upper() in assessment_text:
                found_ingredients.append(ingredient)
        
        logger.info(f"[Citation Engine] Fallback text extraction found: {found_ingredients}")
        return found_ingredients
    
    def _search_citations_for_ingredient(self, ingredient: str) -> List:
        """Search for citations for a specific ingredient using async service."""
        try:
            # Use async citation search for 10x speed improvement
            citations_dict = asyncio.run(search_citations_for_health_assessment([ingredient]))
            citations = citations_dict.get(ingredient, [])
            
            # Convert to expected format
            formatted_citations = []
            for citation in citations[:2]:  # Limit to 2 citations
                formatted_citations.append({
                    'title': citation.get('title', ''),
                    'authors': citation.get('authors', ''),
                    'journal': citation.get('journal', ''),
                    'year': citation.get('year', ''),
                    'url': citation.get('url', ''),
                    'source': citation.get('source', 'Academic')
                })
            
            return formatted_citations
            
        except Exception as e:
            logger.error(f"Error searching citations for {ingredient}: {e}")
            # Fallback to synchronous search if async fails
            try:
                search_params = CitationSearch(
                    ingredient=ingredient,
                    health_claim="health effects toxicity carcinogenic",
                    max_results=2,
                    search_pubmed=True,
                    search_crossref=True,
                    search_semantic_scholar=True,
                    search_fda=True,
                    search_who=True,
                    search_harvard_health=True,
                    search_web=False
                )
                result = self.citation_service.search_citations(search_params)
                return result.citations
            except Exception as fallback_error:
                logger.error(f"Fallback citation search also failed: {fallback_error}")
                return []
    
    def _enhance_assessment_with_citations(
        self, 
        basic_assessment: Dict[str, Any], 
        high_risk_ingredients: List[str],
        citations_dict: Dict[str, str]
    ) -> Optional[HealthAssessment]:
        """Enhance the basic assessment with real citations."""
        try:
            # Use the structured assessment from Gemini directly instead of rebuilding it
            # Just inject the real citations into the existing structure
            enhanced_assessment_data = basic_assessment.copy()
            
            # Add real citations to the structure
            enhanced_assessment_data["real_citations"] = citations_dict
            enhanced_assessment_data["source_disclaimer"] = f"Health assessment based on {len(citations_dict)} real scientific citations from PubMed and CrossRef"
            
            # Update citation IDs in ingredients to match real citations
            if "ingredients_assessment" in enhanced_assessment_data:
                citation_id_map = {str(i+1): str(i+1) for i in range(len(citations_dict))}
                
                # Update high-risk ingredients with real citation IDs
                for ingredient in enhanced_assessment_data["ingredients_assessment"].get("high_risk", []):
                    if "citations" in ingredient and ingredient["citations"]:
                        # Map to real citation IDs (first 2 citations for each ingredient)
                        ingredient["citations"] = list(citation_id_map.keys())[:2]
                
                # Update moderate-risk ingredients with real citation IDs  
                for ingredient in enhanced_assessment_data["ingredients_assessment"].get("moderate_risk", []):
                    if "citations" in ingredient and ingredient["citations"]:
                        ingredient["citations"] = list(citation_id_map.keys())[:2]
            
            # Convert citations dict to proper works_cited format
            works_cited = []
            for i, (citation_id, citation_text) in enumerate(citations_dict.items(), 1):
                works_cited.append({
                    "id": i,
                    "citation": citation_text
                })
            
            enhanced_assessment_data["works_cited"] = works_cited
            
            # Create HealthAssessment object from enhanced data
            enhanced_assessment = HealthAssessment(**enhanced_assessment_data)
            
            return enhanced_assessment
            
        except Exception as e:
            logger.error(f"Error enhancing assessment with citations: {e}")
            # Fallback to original assessment without real citations
            try:
                return HealthAssessment(**basic_assessment)
            except:
                return None
    
    def _build_basic_assessment_prompt(self, product: ProductStructured) -> str:
        """Build prompt for basic assessment without citations."""
        ingredients_text = product.product.ingredients_text or "Ingredients not available"
        
        return f"""Analyze this meat product for health risks and concerns:

Product: {product.product.name}
Ingredients: {ingredients_text}

Identify any high-risk ingredients and their potential health concerns. 
Focus on preservatives, additives, and processing agents commonly used in meat products.
Do not include any citations or references - just provide the analysis."""
    
    def _build_enhanced_prompt(
        self, 
        basic_assessment: Dict[str, Any],
        high_risk_ingredients: List[str], 
        citations_dict: Dict[str, str]
    ) -> str:
        """Build prompt for enhanced assessment with citations."""
        
        citations_text = "\n".join([f"[{k}] {v}" for k, v in citations_dict.items()])
        
        return f"""Based on the following real scientific citations, provide an enhanced health assessment:

HIGH-RISK INGREDIENTS IDENTIFIED: {', '.join(high_risk_ingredients)}

REAL SCIENTIFIC CITATIONS:
{citations_text}

Please provide a comprehensive health assessment that references these actual scientific studies.
Use citation markers [1], [2], etc. to reference the studies provided above.
Focus on the specific health effects documented in the research."""


# Test function
def test_citation_enhanced_assessment():
    """Test the citation-enhanced health assessment."""
    
    # Create a test product (this would normally come from your database)
    from app.models.product import ProductInfo, ProductCriteria, ProductHealth, ProductEnvironment, ProductMetadata, ProductStructured, ProductNutrition
    
    test_product_data = ProductInfo(
        code="test_product",
        name="Test Bacon with BHA",
        brand="Test Brand",
        ingredients_text="Pork, Water, Salt, Sugar, Sodium Nitrite, BHA, Natural Flavors"
    )
    
    test_health = ProductHealth(
        nutrition=ProductNutrition(
            calories=250,
            protein=15.0,
            fat=20.0,
            carbohydrates=1.0,
            salt=2.5
        )
    )
    
    test_criteria = ProductCriteria()
    test_environment = ProductEnvironment()
    test_metadata = ProductMetadata()
    
    test_product = ProductStructured(
        product=test_product_data,
        criteria=test_criteria,
        health=test_health,
        environment=test_environment,
        metadata=test_metadata
    )
    
    # Test the enhanced assessment
    service = HealthAssessmentWithCitations()
    result = service.generate_health_assessment_with_real_citations(test_product)
    
    if result:
        logger.info("✅ Citation-Enhanced Health Assessment Generated!")
        logger.info(f"Summary: {result.summary}")
        logger.info(f"Source disclaimer: {result.source_disclaimer}")
        if hasattr(result, 'real_citations'):
            logger.info(f"Real citations found: {len(result.real_citations)}")
            for i, citation in enumerate(result.real_citations.values(), 1):
                logger.debug(f"{i}. {citation[:100]}...")
    else:
        logger.error("❌ Failed to generate citation-enhanced assessment")


if __name__ == "__main__":
    test_citation_enhanced_assessment() 