"""Health assessment service using Gemini for product analysis."""
import json
import logging
import time
import random
import re
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cache import cache  # Use unified cache
from app.models.product import HealthAssessment, ProductStructured
from app.api.v1.models import EnhancedHealthAssessment, Citation
from app.db import models as db_models
from app.services.health_assessment_with_citations import HealthAssessmentWithCitations

logger = logging.getLogger(__name__)

class HealthAssessmentService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")
        
        # Configure Gemini API key
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.citation_service = HealthAssessmentWithCitations()  # Add citation service

def generate_health_assessment(product: ProductStructured, db: Optional[Session] = None) -> Optional[HealthAssessment]:
    """
    Generate a detailed health assessment for a product using Gemini.
    
    Args:
        product: The structured product data to analyze
        db: Database session for finding similar products for recommendations
        
    Returns:
        HealthAssessment: The AI-generated health assessment or None if generation failed
    """
    if not settings.GEMINI_API_KEY:
        logger.error("Gemini API key not configured")
        return None
    
    # Generate cache key based on product code
    cache_key = cache.generate_key(product.product.code, prefix="health_assessment")
    
    # Check cache first
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.info(f"Returning cached health assessment for product {product.product.code}")
        try:
            return HealthAssessment(**cached_result)
        except ValidationError as e:
            logger.warning(f"Failed to parse cached health assessment: {e}")
            cache.delete(cache_key)  # Remove invalid cache entry
    
    # Get similar products for recommendations if database is available
    similar_products = []
    if db and product.product.meat_type:
        similar_products = _get_similar_products(db, product)
    
    # Format prompt with product data and similar products
    prompt = _build_health_assessment_prompt(product, similar_products)
    
    # Use exponential backoff for rate limit handling
    max_retries = 3
    base_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Call Gemini API
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            response = model.generate_content(prompt)
            
            # Parse and validate response
            assessment = _parse_gemini_response(response.text)
            
            if assessment:
                # Store in cache (24 hour expiration)
                cache.set(cache_key, assessment.dict(), ttl=86400)  # 24 hours
                
            return assessment
        
        except Exception as e:
            # Check if it's a rate limit error
            if "429" in str(e) or "exceeded your current quota" in str(e):
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    # Calculate backoff delay with jitter
                    delay = (base_delay * (2 ** attempt)) + (random.random() * 0.5)
                    logger.warning(f"Rate limit hit. Retrying in {delay:.2f} seconds. Attempt {attempt+1}/{max_retries}")
                    time.sleep(delay)
                else:
                    logger.error(f"Rate limit error after {max_retries} attempts: {e}")
            else:
                logger.error(f"Error generating health assessment: {e}")
                break
    
    # If we reach here, all attempts failed
    return None

def _get_similar_products(db: Session, target_product: ProductStructured) -> List[Dict[str, Any]]:
    """Get similar products from database for recommendations."""
    try:
        # Query products with same meat type, excluding the current product
        similar_products = (
            db.query(db_models.Product)
            .filter(db_models.Product.meat_type == target_product.product.meat_type)
            .filter(db_models.Product.code != target_product.product.code)
            .filter(db_models.Product.ingredients_text.isnot(None))  # Must have ingredients
            .limit(20)  # Get more than needed, let Gemini choose the best
            .all()
        )
        
        # Convert to simplified dict format for Gemini
        products_data = []
        for product in similar_products:
            product_data = {
                "code": product.code,
                "name": product.name,
                "brand": product.brand,
                "meat_type": product.meat_type,
                "risk_rating": product.risk_rating,
                "ingredients_text": product.ingredients_text,
                "image_url": product.image_url,
                "nutrition": {
                    "calories": product.calories,
                    "protein": product.protein,
                    "fat": product.fat,
                    "carbohydrates": product.carbohydrates,
                    "salt": product.salt
                }
            }
            products_data.append(product_data)
        
        logger.info(f"Found {len(products_data)} similar products for recommendations")
        return products_data
        
    except Exception as e:
        logger.error(f"Error getting similar products: {e}")
        return []

def _build_health_assessment_prompt(product: ProductStructured, similar_products: List[Dict[str, Any]]) -> str:
    """Build prompt for Gemini with product data for health assessment."""
    # Extract relevant data for the assessment
    ingredients_text = product.product.ingredients_text or "Ingredients not available"
    
    # Extract nutrition data
    nutrition = {}
    if product.health and product.health.nutrition:
        nutrition = {
            "calories": product.health.nutrition.calories,
            "protein": product.health.nutrition.protein,
            "fat": product.health.nutrition.fat,
            "carbohydrates": product.health.nutrition.carbohydrates,
            "salt": product.health.nutrition.salt
        }
    
    # Get risk rating if available
    risk_rating = None
    if product.criteria and product.criteria.risk_rating:
        risk_rating = product.criteria.risk_rating
    
    # Build product data section
    product_data = {
        "product_name": product.product.name,
        "brand": product.product.brand,
        "ingredients_text": ingredients_text,
        "nutrition": nutrition,
        "risk_rating": risk_rating
    }
    
    # Use the new comprehensive prompt template
    prompt = f"""You are an AI assistant specialized in analyzing meat products and providing health assessments. Your expertise focuses on meat processing, preservation methods, sourcing practices, and meat-specific health considerations. When provided with a JSON payload describing a meat product's ingredient list and nutritional facts, follow the steps below to produce a compact, UI-ready health summary.

Your Tasks:

1. Analyze each ingredient and assign it to one of three risk categories—high_risk, moderate_risk, or low_risk—with special attention to:
   - Meat processing methods (curing, smoking, etc.)
   - Preservatives commonly used in meat products
   - Additives specific to meat processing
   - Sourcing indicators (antibiotics, hormones, etc.)

2. Exclude ingredients from the low_risk group if they have:
   - No health risks or concerns
   - Generic or empty descriptions like "None identified"

3. Do not include alternatives[] in the ingredients_assessment block.

4. Generate a 2–3 sentence plain-language summary of the product's overall health profile, focusing on:
   - Meat processing method and its health implications
   - Sourcing quality (antibiotic-free, grass-fed, etc.)
   - Key preservatives or additives specific to meat products
   - Notable nutritional aspects relevant to meat consumption

5. Create a nutrition_labels array based on the nutrition values provided, with meat-specific terms like:
   - "High Protein"
   - "Lean Cut"
   - "Low Sodium"
   - "High in Saturated Fat"
   - "Good Source of Iron"

6. For every ingredient in high_risk and moderate_risk, return an entry in the ingredient_reports section that includes:
   - title: ingredient name + category
   - summary: short explanation of what it is and why it matters in meat processing
   - health_concerns: bulleted list of concerns (NO citation markers needed)
   - common_uses: where it's commonly used in meat products

7. **RECOMMENDATIONS**: Analyze the provided similar products database and recommend up to 5 healthier alternatives that:
   - Are the same meat type (e.g., beef, chicken)
   - Use better processing methods (e.g., uncured vs cured)
   - Have fewer preservatives or additives
   - Come from better sourcing (e.g., grass-fed, antibiotic-free)
   - Include a summary of why it's a better choice
   If no valid alternatives exist, return an empty array.

8. Add a source disclaimer explaining assessments are based on regulatory guidelines and scientific consensus.

MAIN PRODUCT TO ANALYZE:
{json.dumps(product_data, indent=2)}

SIMILAR PRODUCTS DATABASE FOR RECOMMENDATIONS:
{json.dumps(similar_products, indent=2) if similar_products else "[]"}

Expected Output (as machine-readable JSON only):

{{
  "summary": "This product contains multiple processed ingredients...",
  "risk_summary": {{
    "grade": "C",
    "color": "Yellow"
  }},
  "nutrition_labels": [
    "High Protein",
    "Low Sodium"
  ],
  "ingredients_assessment": {{
    "high_risk": [
      {{
        "name": "Sodium Nitrite",
        "risk_level": "high",
        "category": "preservative",
        "concerns": "Common in cured meats, may form carcinogens when heated"
      }}
    ],
    "moderate_risk": [
      {{
        "name": "Celery Powder",
        "risk_level": "moderate",
        "category": "natural preservative",
        "concerns": "Natural source of nitrates used in meat curing"
      }}
    ],
    "low_risk": [
      {{
        "name": "Sea Salt",
        "risk_level": "low",
        "category": "preservative",
        "concerns": "Traditional meat preservation method"
      }}
    ]
  }},
  "ingredient_reports": {{
    "Sodium Nitrite": {{
      "title": "Sodium Nitrite – Meat Preservative",
      "summary": "Sodium nitrite is a preservative commonly used in cured meats...",
      "health_concerns": [
        "May form nitrosamines (potential carcinogens) when heated",
        "Associated with increased risk of colorectal cancer in high consumption"
      ],
      "common_uses": "Found in bacon, ham, hot dogs, and other cured meats"
    }}
  }},
  "recommendations": [
    {{
      "code": "0025317005104",
      "name": "Organic Grass-Fed Beef Jerky",
      "brand": "Applegate",
      "image_url": "https://example.com/images/beef_jerky.jpg",
      "summary": "This jerky contains no artificial preservatives, has low sodium, and is made with organic grass-fed beef.",
      "nutrition_highlights": [
        "High Protein",
        "No Artificial Preservatives",
        "Grass-Fed Beef"
      ],
      "risk_rating": "Green"
    }}
  ],
  "source_disclaimer": "Health assessments are based on regulatory guidelines from FDA, WHO, CDC, and established scientific consensus. Individual health effects may vary."
}}

CRITICAL GUIDELINES FOR RECOMMENDATIONS:
- Only recommend products with the same meat_type as the main product
- Prioritize products with better processing methods (e.g., uncured over cured)
- Consider sourcing quality (grass-fed, antibiotic-free, etc.)
- Look for products with fewer preservatives and additives
- Ensure recommended products are actually different/better than the main product
- If no suitable alternatives exist, return "recommendations": []
- Maximum 5 recommendations

IMPORTANT: Base all health assessments on general scientific consensus from regulatory bodies (FDA, WHO, CDC) and established research. Do not generate specific citations, studies, or URLs. Focus on providing accurate health information based on established knowledge.

Respond with valid JSON only."""
    
    return prompt

def _parse_gemini_response(response_text: str) -> Optional[HealthAssessment]:
    """Parse Gemini response into structured HealthAssessment."""
    try:
        # Check if the response is wrapped in Markdown code blocks
        text = response_text.strip()
        if text.startswith("```json") and text.endswith("```"):
            # Extract the JSON content from the Markdown code block
            json_content = text[7:-3].strip()  # Remove ```json and ``` markers
            response_data = json.loads(json_content)
        else:
            # Try direct JSON parsing
            response_data = json.loads(text)
        
        # Validate and convert to Pydantic model
        health_assessment = HealthAssessment(**response_data)
        return health_assessment
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return None
    except ValidationError as e:
        logger.error(f"Failed to validate Gemini response against HealthAssessment model: {e}")
        return None

def generate_health_assessment_with_citations_option(
    product: ProductStructured, 
    db: Optional[Session] = None, 
    include_citations: bool = False
) -> Optional[HealthAssessment]:
    """
    Generate health assessment with optional real citations.
    
    Args:
        product: The structured product data to analyze
        db: Database session for finding similar products  
        include_citations: Whether to include real scientific citations
        
    Returns:
        HealthAssessment with or without real citations
    """
    if include_citations:
        logger.info(f"Generating citation-enhanced health assessment for {product.product.code}")
        service = HealthAssessmentService()
        return service.citation_service.generate_health_assessment_with_real_citations(product, db)
    else:
        logger.info(f"Generating standard health assessment for {product.product.code}")
        return generate_health_assessment(product, db)

def convert_to_enhanced_assessment(assessment: HealthAssessment) -> EnhancedHealthAssessment:
    """
    Convert a standard HealthAssessment to an EnhancedHealthAssessment with richer citation metadata.
    
    Args:
        assessment: Standard health assessment object
        
    Returns:
        EnhancedHealthAssessment: Enhanced assessment with detailed citation metadata
    """
    # Extract citations from works_cited and real_citations
    citations = []
    cited_ingredients = []
    citation_sources = []
    
    # Process works_cited entries
    if assessment.works_cited:
        for work in assessment.works_cited:
            # Parse the citation text to extract metadata
            citation_text = work.citation
            
            # Default citation with minimal information
            citation = Citation(
                title="Citation information",
                authors=["Unknown"],
                formatted=citation_text
            )
            
            # Try to extract more metadata if available in real_citations
            if assessment.real_citations and str(work.id) in assessment.real_citations:
                real_citation = assessment.real_citations[str(work.id)]
                
                # Parse the real citation string - typically in APA format
                # Example: "Author, A. (2020). Title. Journal, 10(2), 123-145. doi:10.1000/xyz123"
                try:
                    # Extract DOI if present
                    doi_match = re.search(r'doi:([^\s]+)', real_citation)
                    doi = doi_match.group(1) if doi_match else None
                    
                    # Extract PMID if present
                    pmid_match = re.search(r'PMID:?\s*(\d+)', real_citation)
                    pmid = pmid_match.group(1) if pmid_match else None
                    
                    # Extract year if present
                    year_match = re.search(r'\((\d{4})\)', real_citation)
                    year = int(year_match.group(1)) if year_match else None
                    
                    # Extract journal if present
                    journal_match = re.search(r'\)\.\s*([^\.]+)\,', real_citation)
                    journal = journal_match.group(1).strip() if journal_match else None
                    
                    # Extract title - text between author and journal
                    title_match = re.search(r'\)\.\s*([^\.]+)\.', real_citation)
                    title = title_match.group(1).strip() if title_match else "Unknown title"
                    
                    # Extract authors - text before year
                    authors_text = real_citation.split('(')[0].strip()
                    authors = [a.strip() for a in authors_text.split(',') if a.strip()]
                    if not authors:
                        authors = ["Unknown"]
                    
                    # Create enhanced citation
                    citation = Citation(
                        title=title,
                        authors=authors,
                        journal=journal,
                        year=year,
                        doi=doi,
                        pmid=pmid,
                        formatted=real_citation
                    )
                    
                    # Add to citation sources
                    if doi and "doi.org" not in citation_sources:
                        citation_sources.append("doi.org")
                    if pmid and "pubmed.gov" not in citation_sources:
                        citation_sources.append("pubmed.gov")
                        
                except Exception as e:
                    # If parsing fails, keep the default citation
                    logger.warning(f"Error parsing citation: {e}")
            
            citations.append(citation)
    
    # Extract cited ingredients from ingredient reports
    if assessment.ingredient_reports:
        for ingredient_name in assessment.ingredient_reports:
            # Check if the ingredient report has citations
            report = assessment.ingredient_reports[ingredient_name]
            if report.citations and len(report.citations) > 0:
                cited_ingredients.append(ingredient_name)
    
    # Calculate citation grade based on number and quality of citations
    citation_grade = "N/A"
    citation_count = len(citations)
    
    if citation_count > 0:
        # Count citations with DOIs or PMIDs (higher quality)
        verified_citations = sum(1 for c in citations if c.doi or c.pmid)
        
        if citation_count >= 5 and verified_citations >= 3:
            citation_grade = "A"
        elif citation_count >= 3 and verified_citations >= 2:
            citation_grade = "B"
        elif citation_count >= 1 and verified_citations >= 1:
            citation_grade = "C"
        else:
            citation_grade = "D"
    
    # Create the enhanced assessment
    enhanced = EnhancedHealthAssessment(
        summary=assessment.summary,
        risk_summary=assessment.risk_summary,
        nutrition_labels=assessment.nutrition_labels,
        ingredients_assessment=assessment.ingredients_assessment,
        ingredient_reports=assessment.ingredient_reports,
        recommendations=assessment.recommendations,
        source_disclaimer=assessment.source_disclaimer,
        
        # Enhanced citation fields
        citation_count=citation_count,
        citations=citations,
        citation_grade=citation_grade,
        citation_sources=citation_sources,
        cited_ingredients=cited_ingredients
    )
    
    return enhanced 