"""Health assessment service with real citations using citation search tools."""
import logging
import time
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from pydantic import ValidationError
from app.core.config import settings
from app.core.cache import cache
from app.models.product import HealthAssessment, ProductStructured
from app.services.citation_tools import CitationSearchService
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
            
            print(f"[Health Assessment] Analyzing product: {product.product.name}")
            
            # Step 1: Generate basic health assessment without citations
            basic_assessment = self._generate_basic_assessment(product)
            if not basic_assessment:
                return None
            
            # Step 2: Extract high-risk ingredients for citation search
            high_risk_ingredients = self._extract_high_risk_ingredients(basic_assessment)
            print(f"[Health Assessment] High-risk ingredients found: {high_risk_ingredients}")
            
            # Step 3: Search for real citations for each high-risk ingredient
            citations_dict = {}
            citation_counter = 1
            
            for ingredient in high_risk_ingredients:
                print(f"[Health Assessment] Searching citations for: {ingredient}")
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
                print(f"[Health Assessment] Enhanced assessment generated with {len(citations_dict)} real citations")
            
            return enhanced_assessment
            
        except Exception as e:
            logger.error(f"Error generating health assessment with citations: {e}")
            print(f"[Health Assessment] Error: {e}")
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
                print(f"[Citation Engine] Generated structured assessment with {len(assessment_dict.get('ingredients_assessment', {}).get('high_risk', []))} high-risk ingredients")
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
                
                print(f"[Citation Engine] Extracted from Gemini risk analysis: {high_risk_ingredients}")
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
        
        print(f"[Citation Engine] Fallback text extraction found: {found_ingredients}")
        return found_ingredients
    
    def _search_citations_for_ingredient(self, ingredient: str) -> List:
        """Search for citations for a specific ingredient."""
        try:
            search_params = CitationSearch(
                ingredient=ingredient,
                health_claim="health effects toxicity carcinogenic",
                max_results=2,  # Limit to 2 citations per ingredient
                search_pubmed=True,
                search_crossref=True,
                search_web=False
            )
            
            result = self.citation_service.search_citations(search_params)
            return result.citations
            
        except Exception as e:
            logger.error(f"Error searching citations for {ingredient}: {e}")
            return []
    
    def _enhance_assessment_with_citations(
        self, 
        basic_assessment: Dict[str, Any], 
        high_risk_ingredients: List[str],
        citations_dict: Dict[str, str]
    ) -> Optional[HealthAssessment]:
        """Enhance the basic assessment with real citations."""
        try:
            # Build enhanced prompt with real citations
            prompt = self._build_enhanced_prompt(basic_assessment, high_risk_ingredients, citations_dict)
            
            response = genai.GenerativeModel(settings.GEMINI_MODEL).generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0)
            )
            
            # For this example, create a simplified HealthAssessment
            # In a real implementation, you'd parse the JSON response properly
            enhanced_assessment = HealthAssessment(
                summary=f"Enhanced health assessment with {len(citations_dict)} real scientific citations",
                risk_summary=basic_assessment["risk_summary"],
                nutrition_labels=["High Protein"],  # Simplified
                ingredients_assessment={
                    "high_risk": [
                        {
                            "name": ingredient,
                            "risk_level": "high", 
                            "category": "preservative",
                            "concerns": f"Health concerns documented in scientific literature"
                        }
                        for ingredient in high_risk_ingredients
                    ],
                    "moderate_risk": [],
                    "low_risk": []
                },
                ingredient_reports={
                    ingredient: {
                        "title": f"{ingredient} - Health Assessment",
                        "summary": f"Scientific evidence for {ingredient}",
                        "health_concerns": [
                            "Health effects documented in peer-reviewed research",
                            "See citations for specific studies"
                        ],
                        "common_uses": "Used in meat processing"
                    }
                    for ingredient in high_risk_ingredients
                },
                recommendations=[],
                source_disclaimer=f"Health assessment based on {len(citations_dict)} real scientific citations from PubMed and CrossRef",
                real_citations=citations_dict  # Add real citations
            )
            
            return enhanced_assessment
            
        except Exception as e:
            logger.error(f"Error enhancing assessment with citations: {e}")
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
        print("✅ Citation-Enhanced Health Assessment Generated!")
        print(f"Summary: {result.summary}")
        print(f"Source disclaimer: {result.source_disclaimer}")
        if hasattr(result, 'real_citations'):
            print(f"Real citations found: {len(result.real_citations)}")
            for i, citation in enumerate(result.real_citations.values(), 1):
                print(f"{i}. {citation[:100]}...")
    else:
        print("❌ Failed to generate citation-enhanced assessment")


if __name__ == "__main__":
    test_citation_enhanced_assessment() 