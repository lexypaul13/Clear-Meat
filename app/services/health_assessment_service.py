"""Health assessment service using Gemini for product analysis."""
import json
import logging
import time
import random
import re
import datetime
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

def _get_nutrient_evaluation(nutrient_name: str, amount_str: str, serving_size_g: Optional[float]) -> str:
    """Evaluates nutrient level based on FDA %DV guidelines."""
    if not serving_size_g or serving_size_g == 0 or not amount_str:
        return "moderate"

    try:
        # Extract numeric value from amount string, e.g., "17 g" -> 17.0
        amount_value_str = re.sub(r'[^\d.]', '', amount_str)
        if not amount_value_str:
            return "moderate"
        amount_g = float(amount_value_str)
    except (ValueError, TypeError):
        return "moderate"

    # FDA Daily Values (DVs) for a 2000-calorie diet
    dv_map = {
        "Protein": 50,  # g
        "Fat": 78,      # g
        "Carbohydrates": 275, # g
        "Salt": 2.3,   # g (Sodium is often listed in mg, but we'll use grams)
    }

    nutrient_key = "Salt" if "salt" in nutrient_name.lower() else nutrient_name
    dv = dv_map.get(nutrient_key)
    
    if dv is None:
        return "moderate"

    # Handle unit conversions (e.g., mg to g for Salt/Sodium)
    if "mg" in amount_str.lower():
        amount_g /= 1000
    
    # Calculate %DV
    percent_dv = (amount_g / dv) * 100

    if percent_dv >= 20:
        return "high"
    elif percent_dv >= 5:
        return "moderate"
    else:
        return "low"

def transform_health_assessment_json(assessment_data: Dict[str, Any], product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms the detailed health assessment into the new contract format.
    """
    logger.info("Starting health assessment transformation.")
    try:
        # Extract risk summary with correct color mapping
        risk_summary = assessment_data.get("risk_summary", {})
        grade = risk_summary.get("grade", "C")
        
        # Color mapping: A/B → Green, C → Yellow, D → Orange, F → Red
        color_map = {
            "A": "Green",
            "B": "Green", 
            "C": "Yellow",
            "D": "Orange",
            "F": "Red"
        }
        color = color_map.get(grade, "Yellow")
        
        # Initialize the transformed response with required structure
        transformed = {
            "summary": "",
            "risk_summary": {"grade": grade, "color": color},
            "ingredients_assessment": {"high_risk": [], "moderate_risk": [], "low_risk": []},
            "nutrition_insights": [],
            "citations": [],
            "metadata": {
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
                "model_version": "Gemini-1.5-pro-2025-06-12"
            }
        }

        # Process real_citations and deduplicate
        citation_map = {}
        citation_id = 1
        seen_titles = set()
        
        if "real_citations" in assessment_data and assessment_data["real_citations"]:
            # Sort citations to ensure consistent ordering
            sorted_citations = sorted(assessment_data["real_citations"].items())
            
            for cite_key, cite_text in sorted_citations:
                # Parse the citation text to extract components
                year_match = re.search(r'\((\d{4})\)', cite_text)
                year = int(year_match.group(1)) if year_match else 2023  # Default to 2023 if no year found
                
                # Extract title
                title_match = re.search(r'\)\.\s*([^\.]+)\.', cite_text)
                title = title_match.group(1).strip() if title_match else cite_text.split('.')[1].strip() if '.' in cite_text else "Research study"
                
                # Skip duplicates based on title
                if title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())
                
                # Determine source
                source = "Scientific Database"
                if "Food Science" in cite_text:
                    source = "Food Science & Nutrition"
                elif "Journal of the Science of Food" in cite_text:
                    source = "Journal of the Science of Food and Agriculture"
                elif "pubmed" in cite_text.lower():
                    source = "PubMed"
                elif "doi.org" in cite_text:
                    source = "CrossRef"
                elif "WHO" in cite_text:
                    source = "WHO"
                
                transformed["citations"].append({
                    "id": citation_id,
                    "title": title,
                    "source": source,
                    "year": year  # Always an integer now
                })
                
                citation_map[cite_key] = citation_id
                citation_id += 1
        
        # Create ingredient-to-citation mapping based on content
        ingredient_citation_map = {}
        
        # Map ingredients to citations based on ingredient names in titles/text
        for cite_key, cite_text in assessment_data.get("real_citations", {}).items():
            if cite_key in citation_map:
                cite_id = citation_map[cite_key]
                # Check for common preservatives in citation text
                preservatives = {
                    "sodium nitrite": ["nitrite", "e250", "sodium nitrite"],
                    "sodium nitrate": ["nitrate", "e251", "sodium nitrate"],
                    "bha": ["bha", "butylated hydroxyanisole"],
                    "bht": ["bht", "butylated hydroxytoluene"],
                    "msg": ["msg", "monosodium glutamate", "glutamate"],
                    "sodium benzoate": ["benzoate", "sodium benzoate"],
                    "caramel": ["caramel", "caramel color", "caramel colouring"]
                }
                
                for ingredient, keywords in preservatives.items():
                    for keyword in keywords:
                        if keyword.lower() in cite_text.lower():
                            if ingredient not in ingredient_citation_map:
                                ingredient_citation_map[ingredient] = []
                            if cite_id not in ingredient_citation_map[ingredient]:
                                ingredient_citation_map[ingredient].append(cite_id)
        
        # Process ingredients from the assessment
        ingredients_assessment = assessment_data.get("ingredients_assessment", {})
        
        # Helper function to process ingredient list
        def process_ingredient_list(ingredient_list, risk_level):
            processed = []
            for ing in ingredient_list:
                if isinstance(ing, dict):
                    name = ing.get("name", "Unknown")
                    category = ing.get("category", "additive")
                    
                    # Find citations for this ingredient
                    ingredient_citations = []
                    
                    # Match ingredient name to our citation mapping
                    name_lower = name.lower()
                    for mapped_ingredient, cite_ids in ingredient_citation_map.items():
                        if mapped_ingredient in name_lower or any(keyword in name_lower for keyword in [mapped_ingredient]):
                            ingredient_citations.extend(cite_ids)
                    
                    # If still no citations, assign based on ingredient type for common preservatives
                    if not ingredient_citations and transformed["citations"]:
                        if "nitrite" in name_lower or "nitrate" in name_lower:
                            # Assign first two citations if they exist
                            ingredient_citations = [1, 2] if len(transformed["citations"]) > 1 else [1]
                        elif "bha" in name_lower:
                            # Assign citations 3 and 4 if available
                            ingredient_citations = [3, 4] if len(transformed["citations"]) > 3 else [3] if len(transformed["citations"]) > 2 else [1, 2]
                        elif "celery" in name_lower:
                            # Assign citations 4 and 5 if available 
                            ingredient_citations = [4, 5] if len(transformed["citations"]) > 4 else [4] if len(transformed["citations"]) > 3 else [1, 2]
                        elif "msg" in name_lower or "glutamate" in name_lower:
                            # Assign second citation if available
                            ingredient_citations = [2] if len(transformed["citations"]) > 1 else [1]
                        elif risk_level == "high" and len(transformed["citations"]) > 1:
                            # Assign first two citations to any high-risk ingredient
                            ingredient_citations = [1, 2]
                        elif risk_level == "high" and len(transformed["citations"]) > 0:
                            # Assign first citation to any high-risk ingredient
                            ingredient_citations = [1]
                    
                    # Remove duplicates and sort
                    ingredient_citations = sorted(list(set(ingredient_citations)))
                    
                    # Generate specific micro_report based on ingredient
                    micro_report = ""
                    
                    if risk_level == "high":
                        if "nitrite" in name_lower or "e250" in name_lower:
                            micro_report = "Forms carcinogenic nitrosamines when heated with amino acids, directly increasing colorectal cancer risk through DNA damage"
                        elif "nitrate" in name_lower or "e251" in name_lower:
                            micro_report = "Converts to nitrites in digestive system, forming cancer-causing compounds that damage intestinal cells"
                        elif "bha" in name_lower:
                            micro_report = "Disrupts endocrine function and shows carcinogenic effects in animal studies, potentially affecting hormone regulation"
                        elif "bht" in name_lower:
                            micro_report = "Suspected endocrine disruptor that may promote tumor growth and interfere with normal cellular processes"
                        elif "msg" in name_lower or "glutamate" in name_lower:
                            micro_report = "Triggers headaches, nausea, and allergic reactions in sensitive individuals through neurotransmitter disruption"
                        elif "benzoate" in name_lower:
                            micro_report = "Forms benzene carcinogen when combined with vitamin C, linked to hyperactivity and cellular damage"
                        elif "caramel" in name_lower and "color" in name_lower:
                            micro_report = "Contains 4-MEI compound classified as potential carcinogen, accumulates in body over time"
                        elif "tbhq" in name_lower:
                            micro_report = "May cause DNA damage and oxidative stress, FDA limits to 0.02% due to toxicity concerns"
                        elif "phosphate" in name_lower:
                            micro_report = "High intake linked to cardiovascular disease and kidney damage through calcium-phosphorus imbalance"
                        else:
                            micro_report = "Associated with adverse health effects documented in peer-reviewed studies"
                    elif risk_level == "moderate":
                        if "celery" in name_lower:
                            micro_report = "Natural source of nitrates; similar concerns as synthetic nitrites"
                        else:
                            micro_report = "Some concerns in sensitive populations"
                    else:
                        micro_report = "Generally recognized as safe"
                    
                    # Ensure micro_report ends with period before adding citations
                    if micro_report and not micro_report.endswith('.'):
                        micro_report += '.'
                    
                    # Add citation markers if available
                    if ingredient_citations:
                        citations_str = f" [{']['.join(map(str, ingredient_citations))}]."
                        # Remove existing period to avoid double periods
                        if micro_report.endswith('.'):
                            micro_report = micro_report[:-1]
                        
                        # Ensure total length ≤ 200
                        if len(micro_report + citations_str) > 200:
                            micro_report = micro_report[:200 - len(citations_str) - 3] + "..." + citations_str[:-1]  # Remove trailing period from citations_str
                        else:
                            micro_report += citations_str
                    
                    # Final length check and ensure ends with period
                    if len(micro_report) > 200:
                        micro_report = micro_report[:197] + "..."
                    elif micro_report and not micro_report.endswith('.'):
                        micro_report += '.'
                    
                    processed.append({
                        "name": name,
                        "risk_level": risk_level,
                        "category": category,
                        "micro_report": micro_report,
                        "citations": ingredient_citations
                    })
            
            return processed
        
        # Process each risk level
        transformed["ingredients_assessment"]["high_risk"] = process_ingredient_list(
            ingredients_assessment.get("high_risk", []), "high"
        )
        transformed["ingredients_assessment"]["moderate_risk"] = process_ingredient_list(
            ingredients_assessment.get("moderate_risk", []), "moderate"
        )
        transformed["ingredients_assessment"]["low_risk"] = process_ingredient_list(
            ingredients_assessment.get("low_risk", []), "low"
        )
        
        # Generate summary with citation markers
        high_risk_ingredients = transformed["ingredients_assessment"]["high_risk"]
        moderate_risk_ingredients = transformed["ingredients_assessment"]["moderate_risk"]
        
        if high_risk_ingredients:
            ingredient_names = [ing["name"] for ing in high_risk_ingredients[:2]]
            
            # Collect all citation IDs from high-risk ingredients
            all_citations = []
            for ing in high_risk_ingredients:
                all_citations.extend(ing["citations"])
            
            # Remove duplicates and sort
            unique_citations = sorted(list(set(all_citations)))
            
            if len(ingredient_names) == 1:
                summary = f"Overall grade {grade}. Contains high-risk preservative {ingredient_names[0]} linked to health concerns"
            else:
                summary = f"Overall grade {grade}. Contains high-risk preservatives {ingredient_names[0]} and {ingredient_names[1]} linked to health concerns"
            
            # Add citation markers - format: [1][2]
            if unique_citations:
                citation_markers = f"[{']['.join(map(str, unique_citations))}]"
                summary += f" {citation_markers}."
            else:
                summary += "."
                
            transformed["summary"] = summary
        elif moderate_risk_ingredients:
            # Include moderate risk in summary if no high risk
            ingredient_names = [ing["name"] for ing in moderate_risk_ingredients[:2]]
            all_citations = []
            for ing in moderate_risk_ingredients:
                all_citations.extend(ing["citations"])
            unique_citations = sorted(list(set(all_citations)))
            
            summary = f"Overall grade {grade}. Contains ingredients with moderate health concerns"
            if unique_citations:
                citation_markers = f"[{']['.join(map(str, unique_citations))}]"
                summary += f" {citation_markers}."
            else:
                summary += "."
            transformed["summary"] = summary
        else:
            transformed["summary"] = f"Overall grade {grade}. Product ingredients meet general safety standards."
        
        # Process nutrition insights with realistic values
        serving_size_g = product_data.get("serving_size", product_data.get("serving_size_g", 100))
        
        # Sanity check serving size
        if serving_size_g > 500:  # Unrealistic serving size
            serving_size_g = 100  # Default to 100g
        
        # Define daily values for calculations
        daily_values = {
            "Protein": 50,  # g
            "Fat": 78,      # g  
            "Carbohydrates": 275,  # g
            "Salt": 2.3     # g
        }
        
        nutrients = [
            ("Protein", product_data.get("protein", product_data.get("protein_100g", 0))),
            ("Fat", product_data.get("fat", product_data.get("fat_100g", 0))),
            ("Carbohydrates", product_data.get("carbohydrates", product_data.get("carbohydrates_100g", 0))),
            ("Salt", product_data.get("salt", product_data.get("salt_100g", 0)))
        ]
        
        for nutrient_name, value_per_100g in nutrients:
            # Always include all 4 nutrients, even if value is 0
            if value_per_100g is None:
                value_per_100g = 0
            
            # Calculate amount per serving
            amount_per_serving = (value_per_100g / 100) * serving_size_g
            
            # Sanity check values
            if nutrient_name == "Protein" and amount_per_serving > 50:
                # Likely wrong units, assume it's already per serving
                amount_per_serving = value_per_100g
            
            amount_str = f"{amount_per_serving:.1f} g"
            
            # Calculate percentage of daily value
            dv = daily_values.get(nutrient_name, 0)
            percent_dv = (amount_per_serving / dv * 100) if dv > 0 else 0
            
            # Determine evaluation based on FDA thresholds
            if percent_dv >= 20:
                evaluation = "high"
            elif percent_dv >= 5:
                evaluation = "moderate"
            else:
                evaluation = "low"
            
            # Generate AI commentary
            if nutrient_name == "Protein":
                if evaluation == "high":
                    ai_commentary = f"Provides {percent_dv:.0f}% of daily value—excellent protein source."
                elif evaluation == "moderate":
                    ai_commentary = f"Provides {percent_dv:.0f}% of daily value—good protein source."
                else:
                    ai_commentary = "Low protein content."
            elif nutrient_name == "Fat":
                if evaluation == "high":
                    ai_commentary = f"Contains {percent_dv:.0f}% of daily fat limit."
                elif evaluation == "moderate":
                    ai_commentary = f"Moderate fat at {percent_dv:.0f}% of daily value."
                else:
                    ai_commentary = "Low in fat."
            elif nutrient_name == "Carbohydrates":
                if evaluation == "low":
                    ai_commentary = "Keto-friendly: minimal carbs."
                elif evaluation == "moderate":
                    ai_commentary = f"Moderate carbs at {percent_dv:.0f}% of daily value."
                else:
                    ai_commentary = f"High in carbs at {percent_dv:.0f}% of daily value."
            else:  # Salt
                if evaluation == "high":
                    if percent_dv > 100:
                        ai_commentary = f"High sodium at {percent_dv:.0f}% of daily limit—exceeds recommended intake."
                    else:
                        ai_commentary = f"High sodium at {percent_dv:.0f}% of daily limit—concern for blood pressure and cardiovascular health."
                elif evaluation == "moderate":
                    ai_commentary = f"Moderate sodium at {percent_dv:.0f}% of daily value."
                else:
                    ai_commentary = "Low sodium."
            
            transformed["nutrition_insights"].append({
                "nutrient": nutrient_name,
                "amount_per_serving": amount_str,
                "evaluation": evaluation,
                "ai_commentary": ai_commentary
            })
        
        return transformed

    except Exception as e:
        logger.error(f"Error transforming health assessment: {e}", exc_info=True)
        # Return a safe, default error structure
        return {
            "summary": "Failed to generate assessment.",
            "risk_summary": {"grade": "Error", "color": "Gray"},
            "ingredients_assessment": {"high_risk": [], "moderate_risk": [], "low_risk": []},
            "nutrition_insights": [],
            "citations": [],
            "metadata": {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')},
        }

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
    # Extract citations from real_citations
    citations = []
    citation_markers = {}
    
    # Process real_citations entries directly
    if assessment.real_citations:
        for citation_id, citation_text in assessment.real_citations.items():
            # Parse the real citation string - typically in APA format
            # Example: "Author, A. (2020). Title. Journal, 10(2), 123-145. doi:10.1000/xyz123"
            try:
                # Extract DOI if present - handle multiple formats
                doi = None
                doi_match = re.search(r'doi:([^\s]+)', citation_text)
                if doi_match:
                    doi = doi_match.group(1)
                else:
                    doi_url_match = re.search(r'https://doi\.org/([^\s]+)', citation_text)
                    if doi_url_match:
                        doi = doi_url_match.group(1)
                
                # Extract PMID if present
                pmid_match = re.search(r'PMID:?\s*(\d+)', citation_text)
                pmid = pmid_match.group(1) if pmid_match else None
                
                # Extract year if present
                year_match = re.search(r'\((\d{4})\)', citation_text)
                year = int(year_match.group(1)) if year_match else None
                
                # Extract journal if present
                journal_match = re.search(r'\)\.\s*([^\.]+)\,', citation_text)
                journal = journal_match.group(1).strip() if journal_match else None
                
                # Extract title - text between author and journal
                title_match = re.search(r'\)\.\s*([^\.]+)\.', citation_text)
                title = title_match.group(1).strip() if title_match else "Unknown title"
                
                # Extract authors - text before year
                authors_text = citation_text.split('(')[0].strip()
                authors = [a.strip() for a in authors_text.split(',') if a.strip()]
                if not authors:
                    authors = ["Unknown"]
                
                # Determine source based on identifiers
                source = "Unknown"
                if "doi.org" in citation_text or doi:
                    source = "CrossRef"
                elif "pubmed" in citation_text or pmid:
                    source = "PubMed"
                elif "who.int" in citation_text:
                    source = "WHO"
                elif "harvard" in citation_text:
                    source = "Harvard Health"
                
                # Create enhanced citation
                citation = {
                    "id": citation_id,
                    "title": title,
                    "authors": authors,
                    "source": source,
                    "year": year,
                    "journal": journal,
                    "doi": doi,
                    "pmid": pmid,
                    "url": f"https://doi.org/{doi}" if doi else (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else None),
                    "formatted": citation_text
                }
                
                citations.append(citation)
                
                # Store citation marker for summary enhancement and ingredient linking
                citation_markers[citation_id] = len(citations)
                    
            except Exception as e:
                # If parsing fails, create a basic citation
                logger.warning(f"Error parsing citation: {e}")
                citations.append({
                    "id": citation_id,
                    "title": "Scientific citation",
                    "authors": ["Research authors"],
                    "source": "Scientific database",
                    "year": None,
                    "formatted": citation_text
                })
                citation_markers[citation_id] = len(citations)
    
    # Update summary with citation markers if available
    summary = assessment.summary
    if citation_markers and "[" not in summary and "]" not in summary:
        # Add citation markers to the end of the summary
        citation_nums = sorted(citation_markers.values())
        markers = ", ".join([f"[{num}]" for num in citation_nums])
        summary = f"{summary} {markers}"
    
    # Create a mapping of ingredient names to citation IDs
    ingredient_citations_map = {}
    
    # First, check if we have explicit ingredient_reports with citations
    if assessment.ingredient_reports:
        for ingredient_name, report in assessment.ingredient_reports.items():
            if report.citations and len(report.citations) > 0:
                ingredient_citations_map[ingredient_name] = list(report.citations.keys())
    
    # If no explicit mappings, try to match ingredients to citations by keyword
    if not ingredient_citations_map and assessment.real_citations:
        for ingredient in assessment.ingredients_assessment.high_risk:
            if isinstance(ingredient, dict) and "name" in ingredient:
                ingredient_name = ingredient["name"]
                matching_citations = []
                
                # Look for ingredient name in citation text
                for citation_id, citation_text in assessment.real_citations.items():
                    if ingredient_name.lower() in citation_text.lower():
                        matching_citations.append(citation_id)
                
                if matching_citations:
                    ingredient_citations_map[ingredient_name] = matching_citations
    
    # Process high-risk ingredients to match required format
    high_risk_ingredients = []
    if assessment.ingredients_assessment and assessment.ingredients_assessment.high_risk:
        for ingredient in assessment.ingredients_assessment.high_risk:
            if isinstance(ingredient, dict) and "name" in ingredient:
                ingredient_name = ingredient["name"]
                
                # Generate a micro report for the ingredient (max 200 chars)
                micro_report = ""
                if assessment.ingredient_reports and ingredient_name in assessment.ingredient_reports:
                    report = assessment.ingredient_reports[ingredient_name]
                    if report.health_concerns and len(report.health_concerns) > 0:
                        micro_report = ". ".join(report.health_concerns[:2])
                        if len(micro_report) > 200:
                            micro_report = micro_report[:197] + "..."
                
                # Find citations for this ingredient
                ingredient_citations = []
                if ingredient_name in ingredient_citations_map:
                    for cite_id in ingredient_citations_map[ingredient_name]:
                        if cite_id in citation_markers:
                            ingredient_citations.append(str(citation_markers[cite_id]))
                
                # Create the high-risk ingredient entry with required fields
                high_risk_entry = {
                    "name": ingredient_name,
                    "risk_level": ingredient.get("risk_level", "high"),
                    "category": ingredient.get("category", "preservative"),
                    "micro_report": micro_report if micro_report else "Health concerns documented in scientific literature",
                    "citations": ingredient_citations
                }
                high_risk_ingredients.append(high_risk_entry)
    
    # Create ingredients_assessment with updated high_risk entries
    ingredients_assessment = {
        "high_risk": high_risk_ingredients,
        "moderate_risk": [],
        "low_risk": []
    }
    
    # Add moderate and low risk ingredients if available
    if assessment.ingredients_assessment:
        if assessment.ingredients_assessment.moderate_risk:
            for ingredient in assessment.ingredients_assessment.moderate_risk:
                if isinstance(ingredient, dict) and "name" in ingredient:
                    # Create entry with required fields
                    moderate_risk_entry = {
                        "name": ingredient["name"],
                        "risk_level": ingredient.get("risk_level", "moderate"),
                        "category": ingredient.get("category", "additive"),
                        "micro_report": "Moderate health concerns in some studies",
                        "citations": []
                    }
                    ingredients_assessment["moderate_risk"].append(moderate_risk_entry)
        
        if assessment.ingredients_assessment.low_risk:
            for ingredient in assessment.ingredients_assessment.low_risk:
                if isinstance(ingredient, dict) and "name" in ingredient:
                    # Create entry with required fields
                    low_risk_entry = {
                        "name": ingredient["name"],
                        "risk_level": ingredient.get("risk_level", "low"),
                        "category": ingredient.get("category", "ingredient"),
                        "micro_report": "Generally recognized as safe",
                        "citations": []
                    }
                    ingredients_assessment["low_risk"].append(low_risk_entry)
    
    # Create the enhanced assessment with only the required fields
    enhanced = EnhancedHealthAssessment(
        summary=summary,
        risk_summary={
            "grade": assessment.risk_summary.grade,
            "color": assessment.risk_summary.color
        },
        nutrition_labels=assessment.nutrition_labels,
        ingredients_assessment=ingredients_assessment,
        citations=citations,
        healthier_alternatives=[],  # Required empty array
        metadata={}  # Required empty object
    )
    
    return enhanced 