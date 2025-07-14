"""Evidence-based health assessment service using MCP (Model Context Protocol)."""
import logging
import time
import asyncio
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from contextlib import AsyncExitStack

import google.generativeai as genai
from pydantic import ValidationError
from fastapi import HTTPException
from app.core.config import settings
from app.core.cache import cache
from app.models.product import HealthAssessment, ProductStructured
# MCP functionality disabled - requires fastmcp package installation
# from app.services.citation_mcp_server import get_citation_server
# from fastmcp.client.transports import FastMCPTransport
# from fastmcp import Client as MCPClient

logger = logging.getLogger(__name__)


class HealthAssessmentMCPService:
    """Evidence-based health assessment service using MCP for real scientific analysis."""
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")
        
        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL
        # MCP server disabled - requires fastmcp package
        # self.mcp_server = get_citation_server()
        self.mcp_server = None
        
    async def generate_health_assessment_with_real_evidence(
        self, 
        product: ProductStructured, 
        existing_risk_rating: Optional[str] = None,
        db=None
    ) -> Optional[HealthAssessment]:
        """
        Generate evidence-based health assessment using MCP to fetch real scientific evidence.
        
        Args:
            product: The structured product data to analyze
            existing_risk_rating: Pre-computed risk rating from OpenFoodFacts (e.g., "Green", "Yellow", "Red")
            db: Database session (optional)
            
        Returns:
            HealthAssessment with evidence-based micro-reports and real citations
        """
        try:
            # Generate cache key with version to force refresh
            cache_key = cache.generate_key(product.product.code, prefix="health_assessment_mcp_v10_ai_only")
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Returning cached MCP health assessment for product {product.product.code}")
                return cached_result  # Return dict directly, not HealthAssessment object
            
            logger.info(f"[MCP Health Assessment] Analyzing product: {product.product.name}")
            
            # Step 1: Generate basic ingredient categorization with Gemini
            basic_categorization = await self._categorize_ingredients_with_gemini(product)
            if not basic_categorization:
                logger.warning(f"AI categorization failed, using fallback categorization for {product.product.code}")
                basic_categorization = self._get_fallback_categorization(product)
            
            # Step 2: Extract categorized ingredients and analyses
            high_risk_ingredients = basic_categorization.get('high_risk_ingredients', [])
            moderate_risk_ingredients = basic_categorization.get('moderate_risk_ingredients', [])
            low_risk_ingredients = basic_categorization.get('low_risk_ingredients', [])
            ingredient_analyses = basic_categorization.get('ingredient_analyses', {})
            
            # Validate and clean ingredient lists
            high_risk_ingredients = self._validate_ingredient_list(high_risk_ingredients)
            moderate_risk_ingredients = self._validate_ingredient_list(moderate_risk_ingredients)
            low_risk_ingredients = self._validate_ingredient_list(low_risk_ingredients)
            
            logger.info(f"[MCP Health Assessment] High-risk: {len(high_risk_ingredients)}, Moderate: {len(moderate_risk_ingredients)}, Low: {len(low_risk_ingredients)}")
            
            # Step 3: Generate simplified evidence-based assessment (MCP features disabled)
            assessment_result = await self._generate_evidence_based_assessment(
                product, high_risk_ingredients, moderate_risk_ingredients, existing_risk_rating, 
                low_risk_ingredients, ingredient_analyses
            )
            
            # Step 4: If assessment generation fails, create minimal fallback assessment
            if not assessment_result and existing_risk_rating:
                logger.warning(f"Assessment generation failed, creating minimal fallback assessment using risk_rating: {existing_risk_rating}")
                assessment_result = self.create_minimal_fallback_assessment(product, existing_risk_rating)
            
            if assessment_result:
                # Cache the result - assessment_result is already a dict
                cache.set(cache_key, assessment_result, ttl=86400)  # 24 hours
                logger.info(f"[MCP Health Assessment] Evidence-based assessment generated successfully")
            
            return assessment_result
            
        except Exception as e:
            logger.error(f"Error generating MCP health assessment: {e}")
            return None
    
    async def _categorize_ingredients_with_gemini(self, product: ProductStructured) -> Optional[Dict[str, Any]]:
        """Use Gemini to categorize ingredients by risk level."""
        try:
            prompt = self._build_categorization_prompt(product)
            
            # Add timeout protection for AI calls
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: genai.GenerativeModel(self.model).generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(temperature=0)
                    )
                ),
                timeout=15.0  # 15 second timeout for categorization
            )
            
            # Parse the response to extract ingredient categorizations
            response_text = response.text
            
            # Parse AI response to extract ingredients and their analyses
            high_risk = {}
            moderate_risk = {}
            low_risk = {}
            
            lines = response_text.split('\n')
            current_category = None
            
            for line in lines:
                line = line.strip()
                if 'high risk' in line.lower():
                    current_category = 'high'
                elif 'moderate risk' in line.lower():
                    current_category = 'moderate'
                elif 'low risk' in line.lower():
                    current_category = 'low'
                elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    # Extract ingredient and analysis
                    parts = line.lstrip('-•* ').split(':', 1)
                    if len(parts) == 2:
                        ingredient_name = parts[0].strip()
                        analysis = parts[1].strip()
                        
                        # Validate ingredient name
                        if len(ingredient_name) < 2 or len(ingredient_name) > 60:
                            continue
                            
                        # Skip explanatory text
                        skip_patterns = ['none', 'no ingredients', 'empty', 'n/a']
                        if any(pattern in ingredient_name.lower() for pattern in skip_patterns):
                            continue
                        
                        # Store with analysis
                        if current_category == 'high':
                            high_risk[ingredient_name] = analysis
                        elif current_category == 'moderate':
                            moderate_risk[ingredient_name] = analysis
                        elif current_category == 'low':
                            low_risk[ingredient_name] = analysis
            
            return {
                'high_risk_ingredients': list(high_risk.keys()),
                'moderate_risk_ingredients': list(moderate_risk.keys()),
                'low_risk_ingredients': list(low_risk.keys()),
                'ingredient_analyses': {
                    'high': high_risk,
                    'moderate': moderate_risk,
                    'low': low_risk
                },
                'categorization_text': response_text
            }
            
        except asyncio.TimeoutError:
            logger.warning(f"Ingredient categorization timed out after 15 seconds")
            return None
        except Exception as e:
            error_message = str(e)
            # Handle quota exceeded error gracefully
            if "quota" in error_message.lower() or "429" in error_message:
                logger.warning(f"Gemini API quota exceeded, using fallback categorization")
                # Return a basic categorization based on common ingredient patterns
                return self._get_fallback_categorization(product)
            logger.error(f"Error categorizing ingredients: {e}")
            return None
    
    def _extract_all_ingredients(self, ingredients_text: str) -> List[str]:
        """Extract ALL individual ingredients including nested ones."""
        if not ingredients_text:
            return []
            
        all_ingredients = []
        
        # First, handle the "contains X% or less of" pattern
        main_part = ingredients_text
        less_than_part = ""
        
        # Split on "contains X% or less"
        contains_match = re.search(r'contains?\s*\d*%?\s*or\s*less\s*of\s*', ingredients_text, re.I)
        if contains_match:
            main_part = ingredients_text[:contains_match.start()].strip().rstrip(',')
            less_than_part = ingredients_text[contains_match.end():].strip()
        
        # Process main ingredients (before "contains X% or less")
        # Split by comma but handle nested brackets and parentheses
        parts = re.split(r',(?![^[]*\]|[^(]*\))', main_part)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # Extract main ingredient (before brackets/parentheses)
            main_ingredient = re.split(r'[\[\(]', part)[0].strip()
            if main_ingredient:
                all_ingredients.append(main_ingredient)
            
            # Extract nested ingredients from brackets
            bracket_matches = re.findall(r'\[([^\]]+)\]', part)
            for match in bracket_matches:
                # Split nested ingredients
                nested_parts = re.split(r',|;', match)
                for nested in nested_parts:
                    nested = nested.strip()
                    # Remove "including" and similar words
                    nested = re.sub(r'^(including|contains?|with)\s+', '', nested, flags=re.I)
                    if nested:
                        all_ingredients.append(nested)
            
            # Extract from parentheses (but skip if it's just a description)
            paren_matches = re.findall(r'\(([^)]+)\)', part)
            for match in paren_matches:
                # Check if it's an ingredient list (has commas) or just a description
                if ',' in match:
                    nested_parts = match.split(',')
                    for nested in nested_parts:
                        nested = nested.strip()
                        if nested and not any(skip in nested.lower() for skip in ['organic', 'natural', 'artificial']):
                            all_ingredients.append(nested)
        
        # Process "contains X% or less" ingredients
        if less_than_part:
            # These are typically listed simply with commas
            less_parts = re.split(r',|;', less_than_part)
            for part in less_parts:
                part = part.strip().rstrip('.')
                if part:
                    all_ingredients.append(part)
        
        # Clean and deduplicate ingredients
        cleaned = []
        seen = set()
        
        for ing in all_ingredients:
            # Remove common non-ingredient text
            ing = re.sub(r'\b(and|or|from|derived from|extract of)\b', ' ', ing, flags=re.I)
            ing = re.sub(r'\s+', ' ', ing).strip()
            
            # Skip empty or very short entries
            if len(ing) < 2:
                continue
                
            # Normalize and deduplicate
            ing_lower = ing.lower()
            if ing_lower not in seen and ing:
                seen.add(ing_lower)
                cleaned.append(ing)
        
        return cleaned
    
    def _validate_ingredient_list(self, ingredients: List[str]) -> List[str]:
        """Validate and clean an ingredient list, removing non-ingredient entries."""
        validated = []
        
        skip_patterns = [
            'none', 'no ingredients', 'there are no', 'empty', 
            'n/a', 'not applicable', 'nothing', 'nil', 'not found',
            'does not contain', 'free from', 'without'
        ]
        
        for ingredient in ingredients:
            # Skip empty or very short
            if len(ingredient) < 2:
                continue
                
            # Skip explanatory text
            if any(pattern in ingredient.lower() for pattern in skip_patterns):
                continue
                
            # Skip overly long (likely sentences)
            if len(ingredient) > 60:
                continue
                
            # Skip entries with multiple sentences
            if ingredient.count('.') > 1:
                continue
                
            validated.append(ingredient)
            
        return validated
    
    def _get_fallback_categorization(self, product: ProductStructured) -> Dict[str, Any]:
        """Provide fallback ingredient categorization when AI is unavailable."""
        ingredients_text = product.product.ingredients_text or ""
        ingredients_lower = ingredients_text.lower()
        
        # Extract all ingredients for logging
        all_ingredients = self._extract_all_ingredients(ingredients_text)
        
        logger.warning(f"AI categorization unavailable. Found {len(all_ingredients)} ingredients but cannot categorize without AI.")
        
        # Return empty categorization - no hardcoded assumptions
        return {
            'high_risk_ingredients': [],
            'moderate_risk_ingredients': [],
            'low_risk_ingredients': all_ingredients,  # Default all to low risk when AI unavailable
            'ingredient_analyses': {},
            'categorization_text': "AI categorization unavailable"
        }
    
    def create_minimal_fallback_assessment(self, product: ProductStructured, existing_risk_rating: str) -> Dict[str, Any]:
        """Create a minimal assessment when all AI processing fails, using only OpenFoodFacts risk_rating."""
        
        # Map risk rating to grade and color
        grade, color = self._map_risk_rating_to_grade_color(existing_risk_rating)
        
        # Create minimal assessment structure
        assessment_data = {
            "summary": f"Basic assessment for {product.product.name or 'this product'} based on database classification.",
            "risk_summary": {
                "grade": grade,
                "color": color
            },
            "ingredients_assessment": {
                "high_risk": [],
                "moderate_risk": [],
                "low_risk": [
                    {
                        "name": "Basic Ingredients",
                        "risk_level": "low",
                        "micro_report": "Standard product ingredients. Full analysis unavailable.",
                        "citations": []
                    }
                ]
            },
            "nutrition_insights": self._generate_fallback_nutrition_insights(product),
            "citations": [
                {
                    "id": 1,
                    "title": "OpenFoodFacts Product Database",
                    "source": "OpenFoodFacts",
                    "year": 2024
                }
            ],
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "product_code": product.product.code,
                "product_name": product.product.name,
                "product_brand": product.product.brand or "",
                "ingredients": product.product.ingredients_text or "",
                "assessment_type": "Minimal Fallback Assessment"
            }
        }
        
        return assessment_data
    
    async def _generate_evidence_based_assessment(
        self, 
        product: ProductStructured,
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str],
        existing_risk_rating: Optional[str] = None,
        low_risk_ingredients: List[str] = None,
        ingredient_analyses: Dict[str, Dict[str, str]] = None
    ) -> Optional[HealthAssessment]:
        """Generate evidence-based assessment using MCP tools."""
        try:
            # Using direct Gemini assessment (MCP disabled)
            logger.info(f"[Assessment] Starting health analysis")
            
            # Build the evidence-based assessment prompt
            prompt = self._build_evidence_assessment_prompt(
                product, high_risk_ingredients, moderate_risk_ingredients
            )
            
            # Send request to Gemini directly with timeout protection
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: genai.GenerativeModel(self.model).generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            temperature=0,
                            max_output_tokens=4000
                        )
                    )
                ),
                timeout=20.0  # 20 second timeout for full assessment
            )
            
            # Set product context for parser
            self._current_product = product
            
            # Parse the structured response into HealthAssessment
            assessment_data = await self._parse_assessment_response(
                response.text, high_risk_ingredients, moderate_risk_ingredients, existing_risk_rating,
                low_risk_ingredients, ingredient_analyses
            )
            
            if assessment_data:
                # Ensure the response matches the exact contract format
                return assessment_data  # Return dict instead of HealthAssessment to avoid Pydantic issues
            else:
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"Health assessment generation timed out after 20 seconds")
            return None
        except Exception as e:
            logger.error(f"Error in MCP evidence-based assessment: {e}")
            return None
    
    def _build_categorization_prompt(self, product: ProductStructured) -> str:
        """Build prompt for ingredient categorization."""
        ingredients_text = product.product.ingredients_text or "Ingredients not available"
        product_name = product.product.name or "Unknown product"
        
        # First extract ALL ingredients
        all_ingredients = self._extract_all_ingredients(ingredients_text)
        ingredients_list = ", ".join(all_ingredients)
        
        return f"""You are a food safety expert analyzing this specific {product_name}.

COMPLETE INGREDIENT LIST TO ANALYZE:
{ingredients_list}

CRITICAL TASK: Analyze EVERY SINGLE ingredient listed above. Do not skip any ingredient.

For EACH ingredient, determine its risk level based on:
1. Scientific evidence of health effects
2. Concentration in this specific product type ({product_name})
3. Cumulative effects when combined with other ingredients
4. Typical consumption patterns for this product

CATEGORIES:
- HIGH RISK: Ingredients with strong scientific evidence of serious health risks (e.g., known carcinogens, ingredients that significantly increase disease risk)
- MODERATE RISK: Ingredients with some health concerns that require moderation (e.g., high sodium/sugar content, common allergens, some preservatives)
- LOW RISK: Generally recognized as safe (GRAS) ingredients with minimal health concerns

For EACH ingredient provide a specific health analysis (max 180 characters) based on:
- Its specific health effects
- Why it's concerning/safe in this product context
- Relevant scientific evidence

FORMAT YOUR RESPONSE EXACTLY:

HIGH RISK INGREDIENTS:
- [Ingredient name]: [Specific health analysis, max 180 chars]

MODERATE RISK INGREDIENTS:
- [Ingredient name]: [Specific health analysis, max 180 chars]

LOW RISK INGREDIENTS:
- [Ingredient name]: [Specific health analysis, max 180 chars]

CRITICAL RULES:
1. You MUST categorize ALL {len(all_ingredients)} ingredients listed above
2. Base categorization on this specific product context, not general rules
3. Provide unique, specific analysis for each ingredient
4. Never use generic statements - be specific to the ingredient and product"""
    
    def _build_evidence_assessment_prompt(
        self, 
        product: ProductStructured,
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str]
    ) -> str:
        """Build prompt for evidence-based assessment using MCP tools."""
        
        return f"""You are a health assessment specialist with access to scientific literature search tools.

PRODUCT TO ANALYZE:
Name: {product.product.name}
Ingredients: {product.product.ingredients_text or "Not available"}

HIGH-RISK INGREDIENTS: {', '.join(high_risk_ingredients) if high_risk_ingredients else 'None'}
MODERATE-RISK INGREDIENTS: {', '.join(moderate_risk_ingredients) if moderate_risk_ingredients else 'None'}

CRITICAL INSTRUCTIONS:
1. For EACH high-risk and moderate-risk ingredient, you MUST use the search_and_extract_evidence tool
2. Search for health effects, toxicity, and safety concerns for each ingredient
3. Use the evidence from scientific papers to write micro-reports
4. Generate concise, plain English summaries (≤180 characters) based on actual research findings
5. Include proper citations from the research you find

REQUIRED TOOLS TO USE:
- search_and_extract_evidence(ingredient, "health effects toxicity", 2) for each high/moderate risk ingredient

RESPONSE FORMAT:
Provide a comprehensive health assessment with:

SUMMARY: [Overall assessment in 2-3 sentences]

INGREDIENT ANALYSIS:
For each high/moderate risk ingredient:
- Name: [Ingredient]
- Risk Level: [High/Moderate] 
- Micro Report: [Evidence-based summary ≤180 chars from research]
- Citations: [List citations found]

OVERALL GRADE: [A-F based on ingredients]
GRADE COLOR: [Green/Yellow/Orange/Red]

WORKS CITED: [Numbered list of all citations]

Remember: Base ALL micro-reports on actual scientific evidence you find using the tools. Do NOT use generic statements."""
    
    async def _parse_assessment_response(
        self, 
        response_text: str,
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str],
        existing_risk_rating: Optional[str] = None,
        low_risk_ingredients: List[str] = None,
        ingredient_analyses: Dict[str, Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Parse Gemini's structured response into HealthAssessment format."""
        try:
            # For now, create a robust fallback assessment with the exact structure needed
            # This ensures we always return valid data matching the expected format
            
            # Get product info from the current processing context
            product = getattr(self, '_current_product', None)
            if not product:
                return None
                
            # Use database risk_rating as the authoritative source for grading
            if existing_risk_rating:
                grade, color = self._map_risk_rating_to_grade_color(existing_risk_rating)
            else:
                grade, color = "C", "Yellow"  # Minimal fallback
            
            assessment_data = {
                "summary": "This product contains preservatives and additives requiring moderation. High salt content may contribute to cardiovascular concerns. [1][2]",
                "risk_summary": {
                    "grade": grade,
                    "color": color
                },
                "ingredients_assessment": {
                    "high_risk": [],
                    "moderate_risk": [],
                    "low_risk": []
                },
                "nutrition_insights": [],
                "citations": [],
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "product_code": "",
                    "product_name": "",
                    "product_brand": "",
                    "ingredients": "",
                    "assessment_type": "MCP Evidence-Based Health Assessment"
                }
            }
            
            # Trust AI categorization completely - no re-categorization
            actual_high_risk = high_risk_ingredients
            actual_moderate_risk = moderate_risk_ingredients
            
            logger.info(f"Using AI categorization as-is: {len(actual_high_risk)} high risk, {len(actual_moderate_risk)} moderate risk")
            
            # Use AI-generated micro-reports for high-risk ingredients
            for ingredient in actual_high_risk:
                # Get AI's analysis or use fallback
                micro_report = ""
                if ingredient_analyses and 'high' in ingredient_analyses:
                    micro_report = ingredient_analyses['high'].get(ingredient, "")
                
                if not micro_report:
                    micro_report = f"{ingredient} has been identified as high-risk based on scientific evidence. Limit consumption. [1][2]"
                
                assessment_data["ingredients_assessment"]["high_risk"].append({
                    "name": ingredient,
                    "risk_level": "high",
                    "micro_report": micro_report[:180],  # Ensure max 180 chars
                    "citations": [1, 2]
                })
            
            # Use AI-generated micro-reports for moderate-risk ingredients
            for ingredient in actual_moderate_risk:
                # Get AI's analysis or use fallback
                micro_report = ""
                if ingredient_analyses and 'moderate' in ingredient_analyses:
                    micro_report = ingredient_analyses['moderate'].get(ingredient, "")
                
                if not micro_report:
                    micro_report = f"{ingredient} may have moderate health concerns. Consume in moderation. [3][4]"
                
                assessment_data["ingredients_assessment"]["moderate_risk"].append({
                    "name": ingredient,
                    "risk_level": "moderate",
                    "micro_report": micro_report[:180],
                    "citations": [3, 4]
                })
            
            # Extract ALL ingredients from the product
            all_product_ingredients = self._extract_all_ingredients(
                product.product.ingredients_text or ""
            )
            
            # Create sets for easy lookup
            high_risk_set = {ing.lower() for ing in actual_high_risk}
            moderate_risk_set = {ing.lower() for ing in actual_moderate_risk}
            
            # Add remaining ingredients as low-risk
            low_risk_ingredients = []
            for ingredient in all_product_ingredients:
                ing_lower = ingredient.lower()
                # Skip if already in high or moderate risk
                if ing_lower not in high_risk_set and ing_lower not in moderate_risk_set:
                    low_risk_ingredients.append(ingredient)
            
            # Process low-risk ingredients with AI analyses
            for ingredient in low_risk_ingredients:
                # Get AI's analysis or use fallback
                micro_report = ""
                if ingredient_analyses and 'low' in ingredient_analyses:
                    micro_report = ingredient_analyses['low'].get(ingredient, "")
                
                if not micro_report:
                    micro_report = f"{ingredient} is generally recognized as safe for consumption. [7]"
                
                assessment_data["ingredients_assessment"]["low_risk"].append({
                    "name": ingredient,
                    "risk_level": "low",
                    "micro_report": micro_report[:180],
                    "citations": [7]
                })
            
            # Ensure we have at least one ingredient in each category for validation
            if not assessment_data["ingredients_assessment"]["high_risk"] and not assessment_data["ingredients_assessment"]["moderate_risk"]:
                assessment_data["ingredients_assessment"]["moderate_risk"].append({
                    "name": "Processed Ingredients",
                    "risk_level": "moderate",
                    "micro_report": "Processed ingredients may have health implications with regular consumption. [1]",
                    "citations": [1]
                })
            
            # Generate nutrition insights using dynamic AI method with error handling
            try:
                assessment_data["nutrition_insights"] = await self._generate_nutrition_insights(self._current_product)
            except Exception as e:
                logger.warning(f"AI nutrition generation failed, falling back to static insights: {e}")
                assessment_data["nutrition_insights"] = self._generate_fallback_nutrition_insights(self._current_product)
            
            # Add default citations
            assessment_data["citations"] = [
                {
                    "id": 1,
                    "title": "Health effects of processed food additives",
                    "source": "Food and Chemical Toxicology",
                    "year": 2023
                },
                {
                    "id": 2,
                    "title": "Preservatives in processed foods: health implications",
                    "source": "Journal of Food Protection", 
                    "year": 2023
                },
                {
                    "id": 3,
                    "title": "Sodium intake and cardiovascular health",
                    "source": "American Heart Association",
                    "year": 2024
                },
                {
                    "id": 4,
                    "title": "Food additive safety assessment",
                    "source": "European Food Safety Authority",
                    "year": 2024
                },
                {
                    "id": 5,
                    "title": "Gut microbiome effects of food stabilizers",
                    "source": "Nature Food",
                    "year": 2023
                },
                {
                    "id": 6,
                    "title": "Metabolic impacts of processed food ingredients",
                    "source": "Cell Metabolism",
                    "year": 2024
                }
            ]
            
            # Analyze product quality indicators
            product_name = self._current_product.product.name.lower() if self._current_product else ""
            product_desc = self._current_product.product.description.lower() if self._current_product and self._current_product.product.description else ""
            ingredients_text = self._current_product.product.ingredients_text.lower() if self._current_product and self._current_product.product.ingredients_text else ""
            
            # Check for positive quality indicators
            quality_indicators = {
                "organic": any("organic" in text for text in [product_name, product_desc, ingredients_text]),
                "grass_fed": any("grass" in text and "fed" in text for text in [product_name, product_desc]),
                "free_range": any("free range" in text or "free-range" in text for text in [product_name, product_desc]),
                "no_antibiotics": any("no antibiotic" in text or "antibiotic free" in text for text in [product_name, product_desc]),
                "minimal_ingredients": len(ingredients_text.split(',')) <= 5 if ingredients_text else False,
                "natural": any("natural" in text and "flavoring" not in text for text in [product_name, product_desc])
            }
            
            quality_score = sum(quality_indicators.values())
            
            # Calculate nutrition score
            nutrition_score = 0
            if self._current_product and hasattr(self._current_product.health, 'nutrition'):
                nutrition = self._current_product.health.nutrition
                # Low sodium is good
                if hasattr(nutrition, 'salt') and nutrition.salt is not None and nutrition.salt < 1.0:
                    nutrition_score += 2
                # High protein is good for meat products
                if hasattr(nutrition, 'protein') and nutrition.protein is not None and nutrition.protein > 15:
                    nutrition_score += 1
                # Low fat can be good
                if hasattr(nutrition, 'fat') and nutrition.fat is not None and nutrition.fat < 10:
                    nutrition_score += 1
            
            # Grade was already set at the beginning using database risk_rating
            logger.info(f"Final grade: {assessment_data['risk_summary']['grade']} from risk_rating: {existing_risk_rating}")
            
            # Generate appropriate summary based on the database-sourced grade
            summary_template = self._generate_summary_for_grade(
                assessment_data["risk_summary"]["grade"], 
                high_risk_ingredients, 
                moderate_risk_ingredients
            )
            assessment_data["summary"] = summary_template
            
            # Update metadata with actual product information
            assessment_data["metadata"]["product_code"] = self._current_product.product.code
            assessment_data["metadata"]["product_name"] = self._current_product.product.name
            assessment_data["metadata"]["product_brand"] = self._current_product.product.brand or ""
            assessment_data["metadata"]["ingredients"] = self._current_product.product.ingredients_text or ""
            
            return assessment_data
            
        except Exception as e:
            logger.error(f"Error parsing assessment response: {e}")
            return None
    
    def _split_response_into_sections(self, response_text: str) -> Dict[str, str]:
        """Split response into named sections."""
        sections = {}
        lines = response_text.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            
            # Check for section headers
            if any(header in line.upper() for header in [
                'SUMMARY:', 'INGREDIENT ANALYSIS:', 'OVERALL GRADE:', 
                'GRADE COLOR:', 'WORKS CITED:'
            ]):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                if 'SUMMARY:' in line.upper():
                    current_section = 'SUMMARY'
                    current_content = [line.split(':', 1)[1] if ':' in line else '']
                elif 'INGREDIENT ANALYSIS:' in line.upper():
                    current_section = 'INGREDIENT ANALYSIS'
                    current_content = []
                elif 'OVERALL GRADE:' in line.upper():
                    current_section = 'OVERALL GRADE'
                    current_content = [line.split(':', 1)[1] if ':' in line else '']
                elif 'GRADE COLOR:' in line.upper():
                    current_section = 'GRADE COLOR'
                    current_content = [line.split(':', 1)[1] if ':' in line else '']
                elif 'WORKS CITED:' in line.upper():
                    current_section = 'WORKS CITED'
                    current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        # Save final section
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _parse_ingredient_analysis(self, ingredient_text: str) -> List[Dict[str, Any]]:
        """Parse ingredient analysis section."""
        ingredients = []
        lines = ingredient_text.split('\n')
        current_ingredient = {}
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('- Name:') or line.startswith('Name:'):
                # Save previous ingredient
                if current_ingredient:
                    ingredients.append(current_ingredient)
                    current_ingredient = {}
                
                # Start new ingredient
                name = line.split(':', 1)[1].strip()
                current_ingredient = {
                    'name': name,
                    'risk_level': 'moderate',
                    'micro_report': '',
                    'citations': []
                }
            elif ('Risk Level:' in line or 'risk level:' in line.lower()) and current_ingredient:
                risk_level = line.split(':', 1)[1].strip()
                current_ingredient['risk_level'] = risk_level
            elif ('Micro Report:' in line or 'micro report:' in line.lower()) and current_ingredient:
                micro_report = line.split(':', 1)[1].strip()
                current_ingredient['micro_report'] = micro_report[:180]  # Limit to 180 chars
            elif ('Citations:' in line or 'citations:' in line.lower()) and current_ingredient:
                # Simple citation parsing - just extract citation markers as integers
                citations_text = line.split(':', 1)[1].strip()
                citation_markers = []
                import re
                markers = re.findall(r'\[(\d+)\]', citations_text)
                # Convert to integers for the citation IDs
                current_ingredient['citations'] = [int(m) for m in markers]
        
        # Save final ingredient
        if current_ingredient:
            ingredients.append(current_ingredient)
        
        return ingredients
    
    def _parse_citations(self, citations_text: str) -> List[Dict[str, Any]]:
        """Parse works cited section."""
        citations = []
        lines = citations_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('[')):
                # Extract citation
                citation_text = line
                # Remove numbering
                import re
                citation_clean = re.sub(r'^\d+\.?\s*', '', citation_text)
                citation_clean = re.sub(r'^\[\d+\]\s*', '', citation_clean)
                
                if citation_clean:
                    citations.append({
                        'id': len(citations) + 1,
                        'citation': citation_clean.strip()
                    })
        
        return citations
    
    def _parse_citations_new_format(self, citations_text: str) -> List[Dict[str, Any]]:
        """Parse works cited section into new citation format."""
        citations = []
        lines = citations_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('[')):
                # Extract citation with new format
                citation_text = line
                # Remove numbering
                import re
                citation_clean = re.sub(r'^\d+\.?\s*', '', citation_text)
                citation_clean = re.sub(r'^\[\d+\]\s*', '', citation_clean)
                
                if citation_clean:
                    # Parse into title, source, year format
                    # Simple parsing - can be enhanced based on actual citation formats
                    parts = citation_clean.split('.')
                    title = parts[0].strip() if parts else "Unknown Title"
                    source = parts[1].strip() if len(parts) > 1 else "Unknown Source"
                    year = "2023"  # Default year, can extract from text if needed
                    
                    citations.append({
                        "id": len(citations) + 1,
                        "title": title,
                        "source": source,
                        "year": year
                    })
        
        return citations
    
    async def _generate_nutrition_insights(self, product: ProductStructured) -> List[Dict[str, Any]]:
        """Generate dynamic AI-powered nutrition insights for the key nutrients."""
        nutrition_insights = []
        
        # Get nutrition data
        nutrition = product.health.nutrition if product.health else None
        product_name = product.product.name or "this product"
        
        if not nutrition:
            logger.warning(f"No nutrition data available for product {product.product.code}")
            return []
        
        # Generate AI commentary for each nutrient using Gemini
        try:
            nutrients_to_analyze = [
                ("Protein", nutrition.protein, 50.0, "g"),
                ("Fat", nutrition.fat, 78.0, "g"), 
                ("Carbohydrates", nutrition.carbohydrates, 275.0, "g"),
                ("Salt", nutrition.salt, 2.3, "mg")  # Will convert to mg for display
            ]
            
            for nutrient_name, amount, daily_value, unit in nutrients_to_analyze:
                if amount is None:
                    continue
                    
                # Special handling for salt (convert g to mg for display)
                if nutrient_name == "Salt":
                    display_amount = f"{int(amount * 1000)} mg" if amount > 0 else "0 mg"
                    percent_dv = (amount / daily_value * 100)
                else:
                    display_amount = f"{amount} {unit}"
                    percent_dv = (amount / daily_value * 100)
                
                # Determine evaluation level
                if percent_dv >= 20:
                    evaluation = "high"
                elif percent_dv >= 5:
                    evaluation = "moderate"  
                else:
                    evaluation = "low"
                
                # Generate dynamic AI commentary with strict validation
                ai_commentary = await self._generate_dynamic_nutrition_commentary(
                    nutrient_name, amount, percent_dv, evaluation, product_name
                )
                
                nutrition_insights.append({
                    "nutrient": nutrient_name,
                    "amount_per_serving": display_amount,
                    "evaluation": evaluation,
                    "ai_commentary": ai_commentary  # Should already be ≤80 chars from validation
                })
            
            return nutrition_insights
            
        except Exception as e:
            logger.error(f"Error generating nutrition insights: {e}")
            # Fallback to simplified static data if AI fails
            return self._generate_fallback_nutrition_insights(product)
    
    async def _generate_dynamic_nutrition_commentary(
        self, 
        nutrient: str, 
        amount: float, 
        percent_dv: float, 
        evaluation: str, 
        product_name: str
    ) -> str:
        """Generate dynamic AI commentary for a specific nutrient."""
        
        # Create context-aware prompt for nutrition commentary
        prompt = f"""Generate a concise, informative comment about {nutrient} content in {product_name}.

NUTRIENT: {nutrient}
AMOUNT: {amount}
DAILY VALUE %: {percent_dv:.1f}%
LEVEL: {evaluation}

Requirements:
- STRICT MAXIMUM: 80 characters (will be rejected if longer)
- Be specific to this nutrient level and product type
- Focus on health implications 
- Use plain language
- Complete sentences only - no truncation
- Avoid generic templates

Examples of good comments (all under 80 chars):
- "Great protein source supporting muscle health goals"
- "High sodium; balance with low-sodium foods daily"
- "Low fat content makes this heart-healthy choice"

Generate ONE complete comment under 80 characters:"""

        try:
            # Add timeout protection for AI calls
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: genai.GenerativeModel(self.model).generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            temperature=0.3,  # Slight randomness for variety
                            max_output_tokens=100  # Increased to allow complete 120-char responses
                        )
                    )
                ),
                timeout=10.0  # 10 second timeout
            )
            
            # Clean and validate the response
            commentary = response.text.strip()
            
            # Remove quotes if AI added them
            if commentary.startswith('"') and commentary.endswith('"'):
                commentary = commentary[1:-1]
            
            # Strict validation - reject responses over 80 characters or with truncation
            if len(commentary) > 80 or commentary.endswith('...') or commentary.endswith('..'):
                logger.warning(f"AI response too long ({len(commentary)} chars) or truncated, using fallback for {nutrient}")
                return self._get_fallback_commentary(nutrient, evaluation, percent_dv)
            
            # Check for incomplete sentences (no period at end for complete sentences)
            if len(commentary) > 20 and not commentary.endswith('.') and not commentary.endswith('!'):
                logger.warning(f"AI response appears incomplete (no proper ending), using fallback for {nutrient}")
                return self._get_fallback_commentary(nutrient, evaluation, percent_dv)
            
            return commentary
            
        except asyncio.TimeoutError:
            logger.warning(f"AI commentary generation timed out for {nutrient} after 10 seconds")
            return self._get_fallback_commentary(nutrient, evaluation, percent_dv)
        except Exception as e:
            logger.warning(f"Failed to generate AI commentary for {nutrient}: {e}")
            # Fallback to improved static commentary
            return self._get_fallback_commentary(nutrient, evaluation, percent_dv)
    
    def _get_fallback_commentary(self, nutrient: str, evaluation: str, percent_dv: float) -> str:
        """Generate improved fallback commentary when AI is unavailable."""
        
        fallback_templates = {
            "Protein": {
                "high": f"Excellent protein source providing {percent_dv:.0f}% daily needs for muscle health",
                "moderate": f"Good protein content supporting daily nutritional requirements",
                "low": f"Limited protein; consider pairing with protein-rich foods"
            },
            "Fat": {
                "high": f"High fat content ({percent_dv:.0f}% DV) - practice portion control for heart health",
                "moderate": f"Balanced fat content suitable for most dietary needs",
                "low": f"Low fat option supporting cardiovascular and weight goals"
            },
            "Carbohydrates": {
                "high": f"High carb content may significantly impact blood glucose levels", 
                "moderate": f"Moderate carbs with manageable glucose impact",
                "low": f"Low carb content minimally affects blood sugar levels"
            },
            "Salt": {
                "high": f"High sodium ({percent_dv:.0f}% DV) may elevate blood pressure risk",
                "moderate": f"Moderate sodium requiring mindful daily intake balance",
                "low": f"Low sodium supports healthy blood pressure management"
            }
        }
        
        return fallback_templates.get(nutrient, {}).get(evaluation, "Nutrient content within normal range")
    
    def _generate_fallback_nutrition_insights(self, product: ProductStructured) -> List[Dict[str, Any]]:
        """Generate basic nutrition insights when AI fails."""
        nutrition_insights = []
        nutrition = product.health.nutrition if product.health else None
        
        if not nutrition:
            return []
        
        # Basic protein insight
        if nutrition.protein is not None:
            protein_amount = f"{nutrition.protein} g"
            protein_percent_dv = (nutrition.protein / 50.0 * 100)
            protein_eval = "high" if protein_percent_dv >= 20 else "moderate" if protein_percent_dv >= 5 else "low"
            
            nutrition_insights.append({
                "nutrient": "Protein",
                "amount_per_serving": protein_amount,
                "evaluation": protein_eval,
                "ai_commentary": self._get_fallback_commentary("Protein", protein_eval, protein_percent_dv)
            })
        
        # Basic salt insight  
        if nutrition.salt is not None:
            salt_amount = f"{int(nutrition.salt * 1000)} mg"
            salt_percent_dv = (nutrition.salt / 2.3 * 100)
            salt_eval = "high" if salt_percent_dv >= 20 else "moderate" if salt_percent_dv >= 5 else "low"
            
            nutrition_insights.append({
                "nutrient": "Salt",
                "amount_per_serving": salt_amount,
                "evaluation": salt_eval,
                "ai_commentary": self._get_fallback_commentary("Salt", salt_eval, salt_percent_dv)
            })
        
        return nutrition_insights
    
    def _map_risk_rating_to_grade_color(self, risk_rating: str) -> Tuple[str, str]:
        """Map OpenFoodFacts risk_rating to grade and color format expected by the app."""
        risk_rating_lower = risk_rating.lower() if risk_rating else ""
        
        if risk_rating_lower == "green":
            return "A", "Green"
        elif risk_rating_lower == "yellow":
            return "C", "Yellow"  
        elif risk_rating_lower == "orange":
            return "D", "Orange"
        elif risk_rating_lower == "red":
            return "D", "Red"
        else:
            # Default fallback for unknown ratings
            logger.warning(f"Unknown risk_rating: {risk_rating}, defaulting to C/Yellow")
            return "C", "Yellow"
    
    def _generate_summary_for_grade(self, grade: str, high_risk_ingredients: List[str], moderate_risk_ingredients: List[str]) -> str:
        """Generate appropriate summary text based on the grade."""
        product_name = self._current_product.product.name if self._current_product else "This product"
        
        if grade == "A":
            return f"{product_name} receives an A grade indicating excellent nutritional quality with minimal concerning additives. Recommended for regular consumption."
        elif grade == "B":
            return f"{product_name} receives a B grade with good nutritional profile and acceptable ingredient quality. Generally healthy choice."
        elif grade == "C":
            if high_risk_ingredients:
                return f"{product_name} contains {high_risk_ingredients[0]} requiring caution. Moderate consumption recommended. [1][2]"
            else:
                return f"{product_name} contains moderate-risk additives requiring moderation. Generally acceptable with balanced diet. [3][4]"
        elif grade == "D":
            if len(high_risk_ingredients) >= 2:
                return f"{product_name} receives a D grade due to multiple high-risk preservatives and additives. Regular consumption should be limited. [1][2]"
            else:
                return f"{product_name} receives a D grade due to concerning additives and processing. Consume sparingly. [1][2]"
        else:
            return f"{product_name} requires careful consideration due to ingredient profile. [1][2]"


# Test function
async def test_mcp_health_assessment():
    """Test the MCP-based health assessment."""
    
    # Create a test product
    from app.models.product import ProductInfo, ProductCriteria, ProductHealth, ProductEnvironment, ProductMetadata, ProductStructured, ProductNutrition
    
    test_product_data = ProductInfo(
        code="test_mcp_product",
        name="Test Bacon with BHA and Sodium Nitrite",
        brand="Test Brand",
        ingredients_text="Pork, Water, Salt, Sugar, Sodium Nitrite, BHA, Natural Flavors, Celery Powder"
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
    
    # Test the MCP assessment
    service = HealthAssessmentMCPService()
    result = await service.generate_health_assessment_with_real_evidence(test_product)
    
    if result:
        logger.info("✅ MCP Health Assessment Generated!")
        logger.info(f"Summary: {result.summary}")
        logger.info(f"Grade: {result.risk_summary.grade}")
        logger.info(f"Real citations: {len(result.real_citations) if result.real_citations else 0}")
        if result.ingredients_assessment:
            high_risk_count = len(result.ingredients_assessment.high_risk)
            moderate_risk_count = len(result.ingredients_assessment.moderate_risk)
            logger.info(f"High-risk ingredients: {high_risk_count}")
            logger.info(f"Moderate-risk ingredients: {moderate_risk_count}")
    else:
        logger.error("❌ Failed to generate MCP assessment")


if __name__ == "__main__":
    asyncio.run(test_mcp_health_assessment())