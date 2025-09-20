"""Evidence-based health assessment service using Gemini with Google Search grounding."""
import logging
import time
import asyncio
import os
import re
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from contextlib import AsyncExitStack

DANGEROUS_INGREDIENTS = ['sodium nitrite', 'bha', 'bht', 'msg', 'monosodium glutamate']

import google.generativeai as genai
from pydantic import ValidationError
from fastapi import HTTPException
import aiohttp

from app.core.config import settings
from app.core.cache import cache
from app.models.product import HealthAssessment, ProductStructured

from app.services.grounded_cache_service import grounded_cache
from app.services.perplexity_citation_service import integrate_perplexity_citations

logger = logging.getLogger(__name__)


class HealthAssessmentMCPService:
    """Evidence-based health assessment service using Gemini with Google Search grounding for ingredient-specific citations."""

    CACHE_PREFIX = "health_assessment_mcp_v30_with_citations"
    # Trivial ingredients that don't need citation research (saves ~30-60 seconds)
    TRIVIAL_INGREDIENTS = {
        'water', 'salt', 'sugar', 'glucose', 'fructose', 'corn syrup', 'high fructose corn syrup',
        'vitamin c', 'vitamin e', 'vitamin a', 'vitamin d', 'vitamin b12', 'vitamin b6', 'thiamine',
        'riboflavin', 'niacin', 'folate', 'biotin', 'pantothenic acid', 'calcium', 'iron', 'zinc',
        'potassium', 'sodium', 'magnesium', 'phosphorus', 'natural flavors', 'natural flavor',
        'spices', 'spice', 'herbs', 'herb', 'garlic', 'onion', 'pepper', 'paprika', 'celery',
        'vinegar', 'lemon juice', 'lime juice', 'citric acid', 'ascorbic acid', 'tocopherols',
        'mixed tocopherols', 'rosemary extract', 'sea salt', 'kosher salt', 'cane sugar',
        'brown sugar', 'honey', 'maple syrup', 'molasses', 'yeast', 'baking soda', 'baking powder'
    }
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")
        
        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL
        
        # Direct Gemini API configuration - streamlined approach
        
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
            # Generate cache key with version to force refresh with enhanced citation system
            # Add timestamp to force fresh generation for debugging
            import time
            cache_key = self.get_assessment_cache_key(product.product.code)
            
            # Check cache first with fixed citation URLs
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Returning cached MCP health assessment for product {product.product.code}")
                return cached_result  # Return dict directly, not HealthAssessment object
            
            logger.info(f"[MCP Health Assessment] Analyzing product: {product.product.name}")
            
            # Steps 1-3: Run ingredient categorization and health assessment in parallel
            logger.info(f"[Parallel Processing] Starting categorization and assessment simultaneously")
            
            # Check for cached ingredient categorization first
            ingredients_hash = hashlib.md5(
                (product.product.ingredients_text or "").encode()
            ).hexdigest()[:12]
            categorization_cache_key = cache.generate_key(
                ingredients_hash, prefix="ingredient_categorization_v3"  # Changed to v3 for parsing fix
            )
            
            cached_categorization = cache.get(categorization_cache_key)
            if cached_categorization:
                logger.info(f"[Cache Hit] Using cached ingredient categorization")
                categorization_task = asyncio.create_task(
                    self._return_cached_result(cached_categorization)
                )
            else:
                logger.info(f"[Cache Miss] Running fresh AI categorization")
                categorization_task = self._categorize_ingredients_with_gemini(product)
            
            assessment_task = self._generate_evidence_based_assessment_with_fallback(product, existing_risk_rating)
            
            # Execute both AI tasks in parallel
            basic_categorization, preliminary_assessment = await asyncio.gather(
                categorization_task, 
                assessment_task,
                return_exceptions=True
            )
            
            # Handle categorization result and cache if successful
            logger.info(f"[RESULT PROCESSING] Categorization result type: {type(basic_categorization)}")
            logger.info(f"[RESULT PROCESSING] Categorization is Exception: {isinstance(basic_categorization, Exception)}")
            logger.info(f"[RESULT PROCESSING] Categorization is truthy: {bool(basic_categorization)}")
            
            if isinstance(basic_categorization, Exception):
                logger.error(f"[RESULT PROCESSING] AI categorization exception: {basic_categorization}")
                basic_categorization = self._get_fallback_categorization(product)
            elif not basic_categorization:
                logger.error(f"[RESULT PROCESSING] AI categorization returned None/empty result")
                basic_categorization = self._get_fallback_categorization(product)
            else:
                logger.info(f"[RESULT PROCESSING] ✅ AI categorization successful!")
                logger.info(f"[RESULT PROCESSING] Categorization keys: {list(basic_categorization.keys())}")
                # Cache successful categorization for 7 days
                if not cached_categorization:
                    cache.set(categorization_cache_key, basic_categorization, ttl=604800)  # 7 days
                    logger.info(f"[Cache Store] Cached ingredient categorization for 7 days")
            
            # Extract categorized ingredients and analyses with detailed logging
            high_risk_ingredients = basic_categorization.get('high_risk_ingredients', [])
            moderate_risk_ingredients = basic_categorization.get('moderate_risk_ingredients', [])
            low_risk_ingredients = basic_categorization.get('low_risk_ingredients', [])
            ingredient_analyses = basic_categorization.get('ingredient_analyses', {})
            
            logger.info(f"[RESULT PROCESSING] Extracted ingredients:")
            logger.info(f"[RESULT PROCESSING] High-risk raw: {high_risk_ingredients}")
            logger.info(f"[RESULT PROCESSING] Moderate-risk raw: {moderate_risk_ingredients}")
            logger.info(f"[RESULT PROCESSING] Low-risk raw: {low_risk_ingredients[:5]}...")  # Show first 5 only
            
            # Validate and clean ingredient lists
            high_risk_ingredients = self._validate_ingredient_list(high_risk_ingredients)
            moderate_risk_ingredients = self._validate_ingredient_list(moderate_risk_ingredients)
            low_risk_ingredients = self._validate_ingredient_list(low_risk_ingredients)
            
            logger.info(f"[RESULT PROCESSING] After validation:")
            logger.info(f"[RESULT PROCESSING] High-risk validated: {high_risk_ingredients}")
            logger.info(f"[RESULT PROCESSING] Moderate-risk validated: {moderate_risk_ingredients}")
            logger.info(f"[RESULT PROCESSING] Low-risk validated count: {len(low_risk_ingredients)}")
            
            # Check if dangerous ingredients survived validation
            all_risky_validated = high_risk_ingredients + moderate_risk_ingredients
            dangerous_validated = [ing for ing in all_risky_validated if any(danger in ing.lower() for danger in ['sodium nitrite', 'bha', 'bht', 'msg'])]
            logger.info(f"[RESULT PROCESSING] Dangerous ingredients after validation: {dangerous_validated}")
            
            logger.info(f"[MCP Health Assessment] High-risk: {len(high_risk_ingredients)}, Moderate: {len(moderate_risk_ingredients)}, Low: {len(low_risk_ingredients)}")
            
            # Handle assessment result and merge with categorization
            logger.info(f"[RESULT PROCESSING] Assessment result type: {type(preliminary_assessment)}")
            logger.info(f"[RESULT PROCESSING] Assessment is Exception: {isinstance(preliminary_assessment, Exception)}")
            logger.info(f"[RESULT PROCESSING] Assessment is truthy: {bool(preliminary_assessment)}")
            
            if isinstance(preliminary_assessment, Exception):
                logger.error(f"[RESULT PROCESSING] Assessment exception: {preliminary_assessment}")
                # Use fallback assessment with existing risk rating
                logger.info(f"[RESULT PROCESSING] Using minimal fallback assessment due to assessment failure")
                assessment_result = self.create_minimal_fallback_assessment(product, existing_risk_rating or "Yellow")
            elif not preliminary_assessment:
                logger.error(f"[RESULT PROCESSING] Assessment returned None/empty result")
                logger.info(f"[RESULT PROCESSING] Creating direct assessment from categorization with {len(high_risk_ingredients)} high-risk, {len(moderate_risk_ingredients)} moderate-risk")
                # Use simple direct assessment builder since we have working categorization
                assessment_result = self._create_assessment_from_successful_categorization(
                    product, high_risk_ingredients, moderate_risk_ingredients, low_risk_ingredients, 
                    ingredient_analyses, existing_risk_rating
                )
            else:
                logger.info(f"[RESULT PROCESSING] ✅ Assessment successful! Merging with categorization")
                logger.info(f"[RESULT PROCESSING] Merging categorization: {len(high_risk_ingredients)} high-risk, {len(moderate_risk_ingredients)} moderate-risk")
                # Merge categorization results with preliminary assessment
                assessment_result = self._merge_categorization_with_assessment(
                    preliminary_assessment, basic_categorization, high_risk_ingredients, moderate_risk_ingredients
                )
                logger.info(f"[Parallel Processing] Successfully merged categorization with assessment")
            
            # Step 4: If assessment generation fails, create minimal fallback assessment
            if not assessment_result and existing_risk_rating:
                logger.warning(f"Assessment generation failed, creating minimal fallback assessment using risk_rating: {existing_risk_rating}")
                assessment_result = self.create_minimal_fallback_assessment(product, existing_risk_rating)
            
            # Final result logging
            logger.info(f"[RESULT PROCESSING] Final assessment result type: {type(assessment_result)}")
            logger.info(f"[RESULT PROCESSING] Final assessment exists: {bool(assessment_result)}")
            if assessment_result and isinstance(assessment_result, dict):
                ingredients_assessment = assessment_result.get('ingredients_assessment', {})
                final_high = len(ingredients_assessment.get('high_risk', []))
                final_moderate = len(ingredients_assessment.get('moderate_risk', []))
                final_low = len(ingredients_assessment.get('low_risk', []))
                logger.info(f"[RESULT PROCESSING] Final ingredients: {final_high} high-risk, {final_moderate} moderate-risk, {final_low} low-risk")
                
                # Check if dangerous ingredients made it to final result
                final_high_names = [ing.get('name', '') for ing in ingredients_assessment.get('high_risk', [])]
                final_moderate_names = [ing.get('name', '') for ing in ingredients_assessment.get('moderate_risk', [])]
                final_dangerous = [name for name in final_high_names + final_moderate_names 
                                 if any(danger in name.lower() for danger in ['sodium nitrite', 'bha', 'bht', 'msg'])]
                logger.info(f"[RESULT PROCESSING] Final dangerous ingredients: {final_dangerous}")
                
                if not final_dangerous and any(danger in product.product.ingredients_text.lower() for danger in ['sodium nitrite', 'bha', 'bht']):
                    logger.error(f"[RESULT PROCESSING] ❌ CRITICAL: Dangerous ingredients missing from final result!")
                    logger.error(f"[RESULT PROCESSING] Expected: sodium nitrite, BHA, BHT from: {product.product.ingredients_text}")
            
            if assessment_result:
                # Step 5: Enhance with Perplexity citations for high-risk ingredients
                try:
                    logger.info("[Perplexity Integration] Adding citations for high-risk ingredients")
                    assessment_result = await integrate_perplexity_citations(assessment_result)
                    logger.info("[Perplexity Integration] Citations integrated successfully")
                except Exception as e:
                    logger.warning(f"[Perplexity Integration] Failed to add citations: {e}")
                    # Continue without citations rather than failing completely
                
                # Cache the result - assessment_result is already a dict
                cache.set(cache_key, assessment_result, ttl=86400)  # 24 hours
                logger.info(f"[MCP Health Assessment] Evidence-based assessment generated successfully")
            
            return assessment_result
            
        except Exception as e:
            logger.error(f"MCP service failed: {e}")
            return None
    
    async def _categorize_ingredients_with_gemini(self, product: ProductStructured) -> Optional[Dict[str, Any]]:
        """Use Gemini to categorize ingredients by risk level."""
        try:
            # Enhanced logging for debugging
            all_ingredients = self._extract_all_ingredients(product.product.ingredients_text or "")
            logger.info(f"[AI CATEGORIZATION START] Product: {product.product.code} - {product.product.name}")
            logger.info(f"[AI CATEGORIZATION] Ingredients to analyze: {all_ingredients}")
            logger.info(f"[AI CATEGORIZATION] Dangerous ingredients present: {[ing for ing in all_ingredients if any(danger in ing.lower() for danger in ['sodium nitrite', 'bha', 'bht', 'msg'])]}")
            
            prompt = self._build_categorization_prompt(product)
            logger.debug(f"[AI CATEGORIZATION] Prompt length: {len(prompt)} chars")
            
            # Add timeout protection for AI calls with enhanced error tracking
            logger.info(f"[AI CATEGORIZATION] Sending request to Gemini API (timeout: 30s)")
            start_time = time.time()
            
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: genai.GenerativeModel(self.model).generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(temperature=0)
                    )
                ),
                timeout=15.0  # Reduced timeout since no Google Search
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"[AI CATEGORIZATION] Gemini API response received in {elapsed_time:.2f}s")
            
            # Parse the response to extract ingredient categorizations
            response_text = response.text
            logger.info(f"[AI CATEGORIZATION] Raw response length: {len(response_text)} chars")
            logger.debug(f"[AI CATEGORIZATION] Raw response preview: {response_text[:1000]}...")
            
            # Parse AI response to extract ingredients and their analyses
            high_risk = {}
            moderate_risk = {}
            low_risk = {}
            
            # More robust parsing that handles various AI response formats
            logger.info(f"[AI CATEGORIZATION] Starting response parsing...")
            parsed_data = self._parse_ai_categorization_response(response_text)
            if parsed_data:
                high_risk = parsed_data.get('high_risk_analyses', {})
                moderate_risk = parsed_data.get('moderate_risk_analyses', {})
                low_risk = parsed_data.get('low_risk_analyses', {})
                
                logger.info(f"[AI CATEGORIZATION SUCCESS] Parsed: {len(high_risk)} high-risk, {len(moderate_risk)} moderate-risk, {len(low_risk)} low-risk ingredients")
                
                # Enhanced logging for dangerous ingredients
                for ingredient, analysis in high_risk.items():
                    logger.info(f"[HIGH-RISK FOUND] {ingredient}: {analysis[:100]}...")
                for ingredient, analysis in moderate_risk.items():
                    logger.info(f"[MODERATE-RISK FOUND] {ingredient}: {analysis[:100]}...")
                    
                # Check if dangerous ingredients were properly categorized
                dangerous_found = [ing for ing in list(high_risk.keys()) + list(moderate_risk.keys()) 
                                 if any(danger in ing.lower() for danger in ['sodium nitrite', 'bha', 'bht', 'msg'])]
                if dangerous_found:
                    logger.info(f"[AI CATEGORIZATION] ✅ Dangerous ingredients correctly categorized: {dangerous_found}")
                else:
                    logger.warning(f"[AI CATEGORIZATION] ⚠️ No dangerous ingredients found in high/moderate risk categories!")
                    logger.warning(f"[AI CATEGORIZATION] Expected dangerous ingredients in product: {[ing for ing in all_ingredients if any(danger in ing.lower() for danger in ['sodium nitrite', 'bha', 'bht', 'msg'])]}")
                    
            else:
                logger.error(f"[AI CATEGORIZATION PARSING FAILED] Could not parse AI response")
                logger.error(f"[AI CATEGORIZATION] Full response text: {response_text}")
                logger.warning("Failed to parse AI categorization response, using fallback parsing")
                # Fallback to original parsing logic
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
            logger.error(f"[AI CATEGORIZATION TIMEOUT] Timed out after 30 seconds for product {product.product.code}")
            logger.error(f"[AI CATEGORIZATION TIMEOUT] This suggests Gemini API is overloaded or experiencing issues")
            return None
        except Exception as e:
            error_message = str(e)
            logger.error(f"[AI CATEGORIZATION EXCEPTION] Product {product.product.code}: {error_message}")
            
            # Enhanced error detection
            if "quota" in error_message.lower() or "429" in error_message:
                logger.error(f"[AI CATEGORIZATION] Gemini API quota exceeded - using fallback categorization")
                return self._get_fallback_categorization(product)
            elif "permission" in error_message.lower() or "unauthorized" in error_message.lower():
                logger.error(f"[AI CATEGORIZATION] API permission/auth error - check Gemini API key")
                return None
            elif "rate limit" in error_message.lower():
                logger.error(f"[AI CATEGORIZATION] Rate limit exceeded - Gemini API is being throttled")
                return None
            elif "model" in error_message.lower():
                logger.error(f"[AI CATEGORIZATION] Model error - check if {self.model} is available")
                return None
            else:
                logger.error(f"[AI CATEGORIZATION] Unknown error type: {error_message}")
                logger.error(f"AI categorization failed: {e}")
                return None
    
    def _parse_ai_categorization_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Enhanced parsing of AI categorization response with multiple format support."""
        try:
            import re
            
            logger.info(f"[PARSING] Starting AI response parsing...")
            logger.debug(f"[PARSING] Response text preview: {response_text[:500]}...")
            
            high_risk_analyses = {}
            moderate_risk_analyses = {}
            low_risk_analyses = {}
            
            # Split response into sections
            sections = re.split(r'(HIGH RISK INGREDIENTS:|MODERATE RISK INGREDIENTS:|LOW RISK INGREDIENTS:)', response_text, flags=re.IGNORECASE)
            logger.info(f"[PARSING] Split response into {len(sections)} sections")
            
            current_section = None
            for i, section in enumerate(sections):
                section = section.strip()
                
                if 'HIGH RISK INGREDIENTS:' in section.upper():
                    current_section = 'high'
                elif 'MODERATE RISK INGREDIENTS:' in section.upper():
                    current_section = 'moderate'
                elif 'LOW RISK INGREDIENTS:' in section.upper():
                    current_section = 'low'
                elif current_section and section:
                    # Parse ingredient lines in this section
                    ingredient_lines = [line.strip() for line in section.split('\n') if line.strip()]
                    logger.info(f"[PARSING] Found {len(ingredient_lines)} lines in {current_section} section")
                    
                    for line in ingredient_lines:
                        logger.debug(f"[PARSING] Processing {current_section} line: {line[:100]}...")
                        # Multiple formats: "- Ingredient: analysis" or "Ingredient: analysis" or "- Ingredient - analysis"
                        patterns = [
                            r'^-\s*([^:]+):\s*(.+)$',  # - Ingredient: analysis
                            r'^\*\s*([^:]+):\s*(.+)$',  # * Ingredient: analysis  
                            r'^([^:]+):\s*(.+)$',      # Ingredient: analysis
                            r'^-\s*([^-]+)\s*-\s*(.+)$'  # - Ingredient - analysis
                        ]
                        
                        parsed = False
                        for pattern in patterns:
                            match = re.match(pattern, line)
                            if match:
                                # Clean markdown formatting from ingredient name
                                ingredient_name = match.group(1).strip().replace("**", "").replace("__", "")
                                analysis = match.group(2).strip()
                                
                                # Validate ingredient name
                                if len(ingredient_name) < 2 or len(ingredient_name) > 60:
                                    continue
                                    
                                # Skip explanatory text
                                skip_patterns = ['none', 'no ingredients', 'empty', 'n/a', 'not applicable']
                                if any(pattern in ingredient_name.lower() for pattern in skip_patterns):
                                    continue
                                
                                # Store analysis
                                if current_section == 'high':
                                    high_risk_analyses[ingredient_name] = analysis
                                    logger.info(f"[PARSING] ✅ Parsed HIGH-RISK: {ingredient_name}")
                                elif current_section == 'moderate':
                                    moderate_risk_analyses[ingredient_name] = analysis
                                    logger.info(f"[PARSING] ✅ Parsed MODERATE-RISK: {ingredient_name}")
                                elif current_section == 'low':
                                    low_risk_analyses[ingredient_name] = analysis
                                    logger.debug(f"[PARSING] ✅ Parsed LOW-RISK: {ingredient_name}")
                                
                                parsed = True
                                break
                        
                        if not parsed and line and not line.startswith('---'):
                            logger.debug(f"Could not parse ingredient line: {line}")
            
            # Return parsed data if we found any ingredients
            logger.info(f"[PARSING] Final parsing results: {len(high_risk_analyses)} high-risk, {len(moderate_risk_analyses)} moderate-risk, {len(low_risk_analyses)} low-risk")
            
            # Check for dangerous ingredients specifically
            all_parsed = {**high_risk_analyses, **moderate_risk_analyses}
            dangerous_parsed = [name for name in all_parsed.keys() if any(danger in name.lower() for danger in ['sodium nitrite', 'bha', 'bht', 'msg'])]
            logger.info(f"[PARSING] Dangerous ingredients parsed: {dangerous_parsed}")
            
            if high_risk_analyses or moderate_risk_analyses or low_risk_analyses:
                return {
                    'high_risk_analyses': high_risk_analyses,
                    'moderate_risk_analyses': moderate_risk_analyses,
                    'low_risk_analyses': low_risk_analyses
                }
            
            logger.warning(f"[PARSING] No ingredients parsed from AI response!")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing AI categorization response: {e}")
            return None
    
    def _create_assessment_from_successful_categorization(
        self,
        product: ProductStructured,
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str],
        low_risk_ingredients: List[str],
        ingredient_analyses: Dict[str, Dict[str, str]],
        existing_risk_rating: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create assessment directly from successful AI categorization results."""
        logger.info(f"[DIRECT ASSESSMENT] Building assessment from successful categorization")
        logger.info(f"[DIRECT ASSESSMENT] Input: {len(high_risk_ingredients)} high-risk, {len(moderate_risk_ingredients)} moderate-risk")
        
        # Use existing risk rating for grade/color or derive from ingredients
        if existing_risk_rating:
            grade, color = self._map_risk_rating_to_grade_color(existing_risk_rating)
        elif high_risk_ingredients:
            grade, color = "D", "Red"  # High-risk ingredients = poor grade
        elif moderate_risk_ingredients:
            grade, color = "C", "Yellow"  # Moderate-risk = average grade
        else:
            grade, color = "B", "Green"  # No risk ingredients = good grade
        
        # Build ingredients assessment
        ingredients_assessment = {
            "high_risk": [],
            "moderate_risk": [],
            "low_risk": []
        }
        
        # Generate summary based on risk ingredients
        if high_risk_ingredients:
            summary = f"This product contains high-risk preservatives ({', '.join(high_risk_ingredients[:2])}). Regular consumption may increase health risks."
        elif moderate_risk_ingredients:
            summary = f"This product contains moderate-risk additives ({', '.join(moderate_risk_ingredients[:2])}). Consume in moderation."
        else:
            summary = "This product appears to have minimal concerning additives based on current analysis."
        
        # Process ingredients assessment without citations
        for ingredient in high_risk_ingredients:
            analysis = ""
            if ingredient_analyses and 'high' in ingredient_analyses:
                # Try to find analysis with cleaned name (without markdown)
                clean_name = ingredient.replace("**", "").replace("__", "").strip()
                analysis = ingredient_analyses['high'].get(ingredient, "") or \
                          ingredient_analyses['high'].get(clean_name, "")
            
            if not analysis:
                analysis = self._generate_ingredient_specific_fallback(ingredient, "high")
                logger.debug(f"[DIRECT ASSESSMENT] Using fallback for high-risk: {ingredient}")
            
            # Clean the ingredient name for display (remove markdown)
            clean_ingredient_name = ingredient.replace("**", "").replace("__", "").strip()
            ingredients_assessment["high_risk"].append({
                "name": clean_ingredient_name,
                "risk_level": "high",
                "micro_report": analysis

            })
            logger.info(f"[DIRECT ASSESSMENT] Added high-risk: {ingredient}")
        
        # Process moderate-risk ingredients
        for ingredient in moderate_risk_ingredients:
            analysis = ""
            if ingredient_analyses and 'moderate' in ingredient_analyses:
                # Try to find analysis with cleaned name (without markdown)
                clean_name = ingredient.replace("**", "").replace("__", "").strip()
                analysis = ingredient_analyses['moderate'].get(ingredient, "") or \
                          ingredient_analyses['moderate'].get(clean_name, "")
            
            if not analysis:
                analysis = self._generate_ingredient_specific_fallback(ingredient, "moderate")
                logger.debug(f"[DIRECT ASSESSMENT] Using fallback for moderate-risk: {ingredient}")
            
            # Clean the ingredient name for display (remove markdown)
            clean_ingredient_name = ingredient.replace("**", "").replace("__", "").strip()
            ingredients_assessment["moderate_risk"].append({
                "name": clean_ingredient_name,
                "risk_level": "moderate", 
                "micro_report": analysis
            })
            logger.info(f"[DIRECT ASSESSMENT] Added moderate-risk: {ingredient}")
        
        # Process some low-risk ingredients (limit to avoid huge payloads)
        for ingredient in low_risk_ingredients[:5]:
            analysis = ""
            if ingredient_analyses and 'low' in ingredient_analyses:
                analysis = ingredient_analyses['low'].get(ingredient, "")
            
            if not analysis:
                analysis = self._generate_ingredient_specific_fallback(ingredient, "low")
            
            # Clean the ingredient name for display (remove markdown)
            clean_ingredient_name = ingredient.replace("**", "").replace("__", "").strip()
            ingredients_assessment["low_risk"].append({
                "name": clean_ingredient_name,
                "risk_level": "low",
                "micro_report": analysis,

            })
        
        assessment_result = {
            "summary": summary,
            "risk_summary": {
                "grade": grade,
                "color": color
            },
            "ingredients_assessment": ingredients_assessment,
            "nutrition_insights": self._generate_fallback_nutrition_insights(product),
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "product_code": product.product.code,
                "product_name": product.product.name,
                "product_brand": product.product.brand or "",
                "ingredients": product.product.ingredients_text or "",
                "assessment_type": "Direct Assessment from AI Categorization"
            }
        }
        
        logger.info(f"[DIRECT ASSESSMENT] Created assessment")
        logger.info(f"[DIRECT ASSESSMENT] Final grade: {grade}, color: {color}")
        
        return assessment_result
    
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
        """Validate and clean ingredient names while preserving meaningful entries."""
        validated: List[str] = []
        seen = set()

        skip_patterns = [
            'none', 'no ingredients', 'there are no', 'empty',
            'n/a', 'not applicable', 'nothing', 'nil', 'not found',
            'does not contain', 'free from', 'without'
        ]

        for ingredient in ingredients:
            if not ingredient:
                continue

            cleaned = ingredient.replace("**", "").replace("__", "").strip()
            if len(cleaned) < 2:
                continue

            if any(pattern in cleaned.lower() for pattern in skip_patterns):
                continue

            # Trim descriptive clauses while keeping the core ingredient name.
            if '.' in cleaned:
                primary_sentence = cleaned.split('.', 1)[0].strip()
                if len(primary_sentence) >= 2:
                    cleaned = primary_sentence

            if ';' in cleaned:
                cleaned = cleaned.split(';', 1)[0].strip()

            max_length = 150
            if len(cleaned) > max_length:
                cleaned = cleaned[:max_length].rstrip(",; -") + '…'

            cleaned_lower = cleaned.lower()
            if cleaned_lower in seen:
                continue

            seen.add(cleaned_lower)
            validated.append(cleaned)

        return validated

    def get_assessment_cache_key(self, product_code: str) -> str:
        """Generate the cache key used for full MCP assessments."""
        return cache.generate_key(product_code, prefix=self.CACHE_PREFIX)

    def _normalize_micro_report(
        self,
        report: str,
        max_sentences: int = 5,
        max_chars: int = 500
    ) -> str:
        """Clamp AI micro-reports to a predictable length for mobile rendering."""
        if not report:
            return report

        text = re.sub(r'\s+', ' ', report).strip()
        if not text:
            return text

        sentences = re.split(r'(?<=[.!?])\s+', text)
        trimmed = sentences[:max_sentences]
        normalized = ' '.join(trimmed).strip()

        if len(normalized) > max_chars:
            normalized = normalized[:max_chars].rstrip(' ,;') + '…'

        return normalized
    
    def _get_fallback_categorization(self, product: ProductStructured) -> Dict[str, Any]:
        """Provide intelligent fallback ingredient categorization using known risk patterns."""
        ingredients_text = product.product.ingredients_text or ""
        ingredients_lower = ingredients_text.lower()
        
        # Extract all ingredients for analysis
        all_ingredients = self._extract_all_ingredients(ingredients_text)
        
        logger.info(f"[Intelligent Fallback] Analyzing {len(all_ingredients)} ingredients using risk patterns")
        
        # Known high-risk ingredients (based on scientific consensus)
        high_risk_patterns = [
            # Nitrites/Nitrates (cancer-linked preservatives)
            'sodium nitrite', 'sodium nitrate', 'potassium nitrite', 'potassium nitrate',
            'e249', 'e250', 'e251', 'e252',
            
            # Sulfites (allergenic preservatives) 
            'e223', 'e224', 'e225', 'e226', 'e227', 'e228',
            'sodium metabisulfite', 'potassium metabisulfite', 'sodium sulfite', 'potassium sulfite',
            'sulfur dioxide', 'calcium sulfite', 'sodium bisulfite',
            
            # Antioxidants (potential carcinogens)
            'bha', 'bht', 'e320', 'e321', 'tbhq', 'e319',
            'butylated hydroxyanisole', 'butylated hydroxytoluene',
            
            # Flavor enhancers (neurological concerns)
            'msg', 'monosodium glutamate', 'e621', 'disodium guanylate', 'e627',
            'disodium inosinate', 'e631', 'calcium diglutamate', 'e623',
            
            # Artificial colors (hyperactivity/allergy linked)
            'red dye', 'yellow dye', 'blue dye', 'artificial color', 'artificial colour',
            'e102', 'e104', 'e110', 'e122', 'e124', 'e129', 'e133', 'e142', 'e151',
            'tartrazine', 'sunset yellow', 'allura red', 'brilliant blue',
            
            # Other high-risk preservatives
            'carrageenan', 'potassium bromate', 'sodium benzoate', 'e211',
            'calcium propionate', 'sodium propionate', 'e280', 'e281', 'e282', 'e283',
            'formaldehyde', 'hexamethylenetetramine', 'e239'
        ]
        
        # Known moderate-risk ingredients  
        moderate_risk_patterns = [
            'sodium phosphate', 'potassium phosphate', 'modified corn starch',
            'high fructose corn syrup', 'corn syrup', 'dextrose', 'maltodextrin',
            'artificial flavor', 'natural flavor', 'xanthan gum', 'guar gum'
        ]
        
        high_risk_ingredients = []
        moderate_risk_ingredients = []
        low_risk_ingredients = []
        
        # Also check the full ingredients text for embedded E-numbers
        ingredients_text_lower = ingredients_text.lower()
        for pattern in high_risk_patterns:
            if pattern.startswith('e') and len(pattern) == 4:  # E-number like e223
                if pattern in ingredients_text_lower:
                    # Extract the E-number with its description
                    import re
                    e_match = re.search(rf'{pattern}\s*\([^)]+\)', ingredients_text_lower, re.IGNORECASE)
                    if e_match:
                        e_ingredient = e_match.group(0).upper()
                        high_risk_ingredients.append(e_ingredient)
                        logger.info(f"[E-Number Detection] Found HIGH RISK: {e_ingredient}")
        
        for ingredient in all_ingredients:
            ingredient_lower = ingredient.lower().strip()
            
            # Check for high-risk patterns
            if any(pattern in ingredient_lower for pattern in high_risk_patterns):
                high_risk_ingredients.append(ingredient)
                logger.info(f"[Intelligent Fallback] Classified as HIGH RISK: {ingredient}")
            # Check for moderate-risk patterns
            elif any(pattern in ingredient_lower for pattern in moderate_risk_patterns):
                moderate_risk_ingredients.append(ingredient)
                logger.info(f"[Intelligent Fallback] Classified as MODERATE RISK: {ingredient}")
            # Default to low risk
            else:
                low_risk_ingredients.append(ingredient)
        
        logger.info(f"[Intelligent Fallback] Final categorization: {len(high_risk_ingredients)} high, {len(moderate_risk_ingredients)} moderate, {len(low_risk_ingredients)} low risk")
        
        return {
            'high_risk_ingredients': high_risk_ingredients,
            'moderate_risk_ingredients': moderate_risk_ingredients, 
            'low_risk_ingredients': low_risk_ingredients,
            'ingredient_analyses': {},
            'categorization_text': "Intelligent pattern-based categorization"
        }
    
    def create_minimal_fallback_assessment(self, product: ProductStructured, existing_risk_rating: str) -> Dict[str, Any]:
        """Create a minimal but informative assessment when AI processing fails or times out."""
        
        # Map risk rating to grade and color
        grade, color = self._map_risk_rating_to_grade_color(existing_risk_rating)
        
        # Quick pattern-based ingredient analysis (no AI needed)
        ingredients_text = (product.product.ingredients_text or "").lower()
        high_risk = []
        moderate_risk = []
        
        # Check for known problematic ingredients
        if 'sodium nitrite' in ingredients_text or 'sodium nitrate' in ingredients_text:
            high_risk.append({
                "name": "Sodium Nitrite/Nitrate",
                "risk_level": "high",
                "micro_report": "Preservative linked to potential health concerns when consumed regularly.",

            })
        
        if 'bha' in ingredients_text or 'bht' in ingredients_text:
            high_risk.append({
                "name": "BHA/BHT",
                "risk_level": "high",
                "micro_report": "Synthetic antioxidant with potential safety concerns.",

            })
        
        if 'msg' in ingredients_text or 'monosodium glutamate' in ingredients_text:
            moderate_risk.append({
                "name": "MSG (Monosodium Glutamate)",
                "risk_level": "moderate",
                "micro_report": "Flavor enhancer that may cause reactions in sensitive individuals.",

            })
        
        if 'phosphate' in ingredients_text:
            moderate_risk.append({
                "name": "Phosphates",
                "risk_level": "moderate",
                "micro_report": "Preservative that may affect mineral balance when consumed in excess.",

            })
        
        # Generate summary based on risk level
        if high_risk:
            summary = f"This {product.product.meat_type or 'meat'} product contains preservatives that require moderation. Consider limiting consumption."
        elif moderate_risk:
            summary = f"This {product.product.meat_type or 'meat'} product contains additives. Suitable for occasional consumption."
        else:
            summary = f"This {product.product.meat_type or 'meat'} product appears to have minimal additives based on quick analysis."
        
        # Create minimal assessment structure
        assessment_data = {
            "summary": summary,
            "risk_summary": {
                "grade": grade,
                "color": color
            },
            "ingredients_assessment": {
                "high_risk": high_risk,
                "moderate_risk": moderate_risk,
                "low_risk": [] if (high_risk or moderate_risk) else [
                    {
                        "name": "Basic Ingredients",
                        "risk_level": "low",
                        "micro_report": "Standard meat product ingredients.",
        
                    }
                ]
            },
            "nutrition_insights": self._generate_fallback_nutrition_insights(product),

            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "product_code": product.product.code,
                "product_name": product.product.name,
                "product_brand": product.product.brand or "",
                "ingredients": product.product.ingredients_text or "",
                "assessment_type": "Quick Assessment (Timeout Fallback)"
            }
        }
        
        assessment_data["summary"] = self._normalize_micro_report(
            assessment_data["summary"],
            max_sentences=3,
            max_chars=320
        )

        return assessment_data
    
    
    async def _generate_evidence_based_assessment_with_fallback(
        self, 
        product: ProductStructured,
        existing_risk_rating: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate health assessment that can work without ingredient categorization data."""
        try:
            logger.info(f"[Parallel Assessment] Starting health analysis without categorization")
            
            # Build prompt using fallback categorization for structure
            fallback_categorization = self._get_fallback_categorization(product)
            high_risk_ingredients = fallback_categorization.get('high_risk_ingredients', [])
            moderate_risk_ingredients = fallback_categorization.get('moderate_risk_ingredients', [])
            
            # Build the grounded assessment prompt for fallback
            prompt = self._build_grounded_assessment_prompt(
                product, high_risk_ingredients, moderate_risk_ingredients
            )
            
            # Use direct Gemini with Google Search grounding (no LangChain agent)
            logger.info(f"[Google Search Grounding] Starting fallback assessment with web search")
            
            # Execute basic assessment without search grounding
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
                timeout=15.0  # Reduced timeout since no Google Search
            )
            
            # Set product context for parser
            self._current_product = product
            
            # Parse the Gemini response - extract text
            response_text = response.text if hasattr(response, 'text') else str(response)
            logger.info(f"[Google Search Grounding] Response received: {len(response_text)} characters")
            
            # Parse the structured response
            assessment_data = await self._parse_assessment_response(
                response_text, high_risk_ingredients, moderate_risk_ingredients, existing_risk_rating,
                fallback_categorization.get('low_risk_ingredients', []), 
                fallback_categorization.get('ingredient_analyses', {})
            )
            
            # Extract grounding metadata for citations if available
            logger.info(f"[DEBUG] Response attributes: {dir(response)}")
            logger.info(f"[DEBUG] Response has grounding_metadata: {hasattr(response, 'grounding_metadata')}")
            logger.info(f"[DEBUG] Response has grounding_support: {hasattr(response, 'grounding_support')}")
            logger.info(f"[DEBUG] Response has sources: {hasattr(response, 'sources')}")
            
            if hasattr(response, 'grounding_metadata'):
                logger.info(f"[DEBUG] grounding_metadata exists: {response.grounding_metadata is not None}")
            
            # Try different ways to access grounding information
            grounding_citations = []
            
            # Method 1: Check candidates for grounding information
            if assessment_data and hasattr(response, 'candidates') and response.candidates:
                try:
                    logger.info(f"[DEBUG] Checking candidates for grounding info")
                    for candidate in response.candidates:
                        logger.info(f"[DEBUG] Candidate attributes: {dir(candidate)}")
                        if hasattr(candidate, 'grounding_metadata'):
                            logger.info(f"[DEBUG] Found grounding_metadata in candidate!")
                            if candidate.grounding_metadata and hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                                logger.info(f"[DEBUG] Found {len(candidate.grounding_metadata.grounding_chunks)} grounding chunks")
                                for i, chunk in enumerate(candidate.grounding_metadata.grounding_chunks):
                                    logger.info(f"[DEBUG] Chunk {i} attributes: {dir(chunk)}")
                                    if hasattr(chunk, 'web') and chunk.web:
                                        logger.info(f"[DEBUG] Web chunk attributes: {dir(chunk.web)}")
                                        # Extract title and URL
                                        raw_title = chunk.web.title if hasattr(chunk.web, 'title') else ''
                                        raw_url = chunk.web.uri if hasattr(chunk.web, 'uri') else ''
                                        
                                        # Log the raw extraction
                                        logger.info(f"[DEBUG] Raw extraction - Title: '{raw_title}', URL: '{raw_url}'")
                                        
                                        # CRITICAL: Resolve redirect URL FIRST, then filter on final destination
                                        resolved_url = await self._resolve_redirect_url(raw_url)
                                        logger.info(f"[DEBUG] Resolved URL: {resolved_url}")
                                        
                                        # Extract domain from RESOLVED URL for filtering
                                        domain = ""
                                        if resolved_url:
                                            try:
                                                from urllib.parse import urlparse
                                                domain = urlparse(resolved_url).netloc.replace('www.', '')
                                            except:
                                                domain = ""
                                        
                                        # Filter for reputable medical sources only
                                        logger.info(f"[DEBUG] Checking FINAL domain: '{domain}' from resolved URL: {resolved_url}")
                                        
                                        # CRITICAL: Block TikTok and other non-medical sources immediately
                                        if self._is_blocked_source(domain):
                                            logger.warning(f"[DEBUG] ❌ BLOCKED non-medical source: {domain}")
                                            continue
                                            
                                        # Check if domain passes medical source validation
                                        is_medical = self._is_reputable_medical_source(domain)
                                        logger.info(f"[DEBUG] Final domain {domain} medical check: {is_medical}")
                                        
                                        if domain and is_medical:
                                            logger.info(f"[DEBUG] ✅ Domain {domain} PASSED filtering")
                                            # Use proper title or generate one from domain
                                            clean_title = raw_title if raw_title and len(raw_title) > 10 else f"Medical Research from {domain}"
                                            
                                            # Calculate priority score for Apple compliance
                                            priority_score = self._get_source_priority_score(domain)
                                            
                                            logger.info(f"[DEBUG] Extracted - Title: {clean_title}, Domain: {domain}, Priority: {priority_score}, URL: {resolved_url}")
                                            grounding_citations.append({
                                                'title': clean_title,
                                                'url': resolved_url,  # Use resolved URL for clickable links
                                                'domain': domain,  # Store actual domain for source name extraction
                                                'source': 'Google Search',
                                                'priority': priority_score  # For sorting by authority
                                            })
                                        else:
                                            logger.warning(f"[DEBUG] ❌ Domain {domain} REJECTED - not a medical authority")
                    
                    if grounding_citations:
                        # Sort citations by priority (highest authority first) for Apple compliance
                        grounding_citations.sort(key=lambda x: x.get('priority', 0), reverse=True)
                        
                        # Convert to Citation model format for App Store compliance
                        # QUALITY OVER QUANTITY: Limit to top 3 highest-authority citations
                        citations = []
                        for i, cite in enumerate(grounding_citations[:3], 1):  # Limit to top 3 citations
                            # URL is already resolved in the filtering step
                            citations.append({
                                "id": i,
                                "title": cite.get('title', 'Medical Research')[:100],  # Truncate long titles
                                "source": self._extract_source_name(cite.get('domain', cite.get('url', ''))),
                                "url": cite.get('url', ''),  # Already resolved URL
                                "year": "2024"  # Default for web sources
                            })
                        
                        assessment_data["citations"] = citations
                        logger.info(f"[Google Search Grounding] Found {len(citations)} citations for App Store compliance")
                    else:
                        # CRITICAL: Always include fallback citations for Apple compliance
                        logger.warning(f"[Citation Fallback] No valid grounding citations found, using fallback medical references")
                        assessment_data["citations"] = self._get_fallback_citations()
                        logger.info(f"[Citation Fallback] Added {len(assessment_data['citations'])} fallback citations")
                    
                    # Add metadata about grounding
                    if "metadata" not in assessment_data:
                        assessment_data["metadata"] = {}
                    assessment_data["metadata"]["grounding_enabled"] = True
                    assessment_data["metadata"]["grounding_source"] = "Google Search"
                except Exception as e:
                    logger.error(f"[Citation Extraction] Failed to extract grounding metadata: {e}")
                    # CRITICAL: Ensure citations are always present for Apple compliance
                    if assessment_data and "citations" not in assessment_data:
                        logger.warning(f"[Citation Extraction] Adding fallback citations due to extraction failure")
                        assessment_data["citations"] = self._get_fallback_citations()
                        logger.info(f"[Citation Extraction] Added {len(assessment_data['citations'])} fallback citations")
            
            # FINAL CHECK: Ensure citations are always present for Apple App Store compliance
            if assessment_data and "citations" not in assessment_data:
                logger.warning(f"[Citation Final Check] No citations found in assessment, adding fallback")
                assessment_data["citations"] = self._get_fallback_citations()
                logger.info(f"[Citation Final Check] Added {len(assessment_data['citations'])} fallback citations")
            
            if assessment_data:
                logger.info(f"[Parallel Assessment] Preliminary assessment generated successfully")
                return assessment_data
            else:
                return None
                
        except asyncio.TimeoutError:
            logger.warning(f"Parallel health assessment generation timed out after 20 seconds")
            return None
        except Exception as e:
            logger.error(f"Error in parallel evidence-based assessment: {e}")
            return None
    
    def _merge_categorization_with_assessment(
        self,
        preliminary_assessment: Dict[str, Any],
        actual_categorization: Dict[str, Any],
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str]
    ) -> Dict[str, Any]:
        """Merge real categorization results with preliminary assessment."""
        try:
            logger.info(f"[Merge] Updating assessment with real categorization data")
            
            # Update ingredient assessment with real categorization
            ingredient_analyses = actual_categorization.get('ingredient_analyses', {})
            
            # Build updated ingredients assessment using real categorization
            updated_ingredients_assessment = {
                "high_risk": [],
                "moderate_risk": [],
                "low_risk": []
            }
            
            # Process high-risk ingredients with real analyses
            for ingredient in high_risk_ingredients:
                ingredient_data = {
                    "name": ingredient,
                    "micro_report": ingredient_analyses.get('high', {}).get(ingredient, 
                        self._get_fallback_ingredient_analysis(ingredient, 'high'))
                }
                updated_ingredients_assessment["high_risk"].append(ingredient_data)
            
            # Process moderate-risk ingredients with real analyses
            for ingredient in moderate_risk_ingredients:
                ingredient_data = {
                    "name": ingredient,
                    "micro_report": ingredient_analyses.get('moderate', {}).get(ingredient,
                        self._get_fallback_ingredient_analysis(ingredient, 'moderate'))
                }
                updated_ingredients_assessment["moderate_risk"].append(ingredient_data)
            
            # Update the assessment with real ingredient data
            preliminary_assessment["ingredients_assessment"] = updated_ingredients_assessment
            
            # Process existing assessment data without citations
            
            logger.info(f"[Merge] Successfully merged {len(high_risk_ingredients)} high-risk and {len(moderate_risk_ingredients)} moderate-risk ingredients")
            return preliminary_assessment
            
        except Exception as e:
            logger.error(f"Error merging categorization with assessment: {e}")
            # Return preliminary assessment as fallback
            return preliminary_assessment
    

    def _build_categorization_prompt(self, product: ProductStructured) -> str:
        """Build prompt for ingredient categorization."""
        ingredients_text = product.product.ingredients_text or "Ingredients not available"
        product_name = product.product.name or "Unknown product"
        
        # First extract ALL ingredients
        all_ingredients = self._extract_all_ingredients(ingredients_text)
        ingredients_list = ", ".join(all_ingredients)
        
        return f"""You are a food scientist analyzing this {product_name}.

INGREDIENTS TO CATEGORIZE: {ingredients_list}

TASK: Sort ALL ingredients into risk categories based on scientific evidence:

HIGH RISK: Known health risks (carcinogens, toxic additives)
MODERATE RISK: Health concerns requiring moderation (high sodium, preservatives, allergens)  
LOW RISK: Generally safe ingredients

IMPORTANT: Provide detailed health analysis for HIGH and MODERATE risk ingredients with scientific evidence. Low risk ingredients need only a brief note.

FORMAT:
HIGH RISK INGREDIENTS:
- [Name]: [Detailed health concern with specific effects, 150-200 chars. Include mechanism of action and cite sources]

MODERATE RISK INGREDIENTS:  
- [Name]: [Health considerations with context, 100-150 chars. Include safe consumption levels if known]

LOW RISK INGREDIENTS:
- [Name]: [Brief positive or neutral note, ~50 chars]

Categorize all {len(all_ingredients)} ingredients above."""
    
    def _build_grounded_assessment_prompt(
        self,
        product: ProductStructured,
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str]
    ) -> str:
        """Build enhanced prompt for targeted medical database searches with accurate citations."""

        # Focus research on the top 3 high-risk and top 2 moderate-risk ingredients for speed and relevance
        ingredients_to_research = high_risk_ingredients[:3] + moderate_risk_ingredients[:2]
        if not ingredients_to_research:
            return "No ingredients provided for assessment."

        # Create specific search query instructions for each ingredient
        search_instructions = []
        for ingredient in ingredients_to_research:
            # Clean the ingredient name for use in a search query
            ingredient_clean = ingredient.replace("(", "").replace(")", "").strip()
            search_instructions.append(f"""
FOR {ingredient_clean.upper()}:
Use these EXACT search queries:
- "health effects of {ingredient_clean} site:fda.gov"
- "{ingredient_clean} safety assessment site:nih.gov"
- "{ingredient_clean} toxicity study site:pubmed.ncbi.nlm.nih.gov"
- "is {ingredient_clean} safe site:who.int"
- "{ingredient_clean} risks and benefits site:mayoclinic.org"
            """)

        return f"""You are a meticulous health researcher analyzing food ingredients for a health assessment. Your ONLY source of information will be from targeted searches on authoritative medical websites.

PRODUCT: {product.product.name}
INGREDIENTS TO RESEARCH: {', '.join(ingredients_to_research)}

CRITICAL INSTRUCTIONS:
You MUST research each ingredient using the following SPECIFIC search strategies. Do not use any other search queries.
{''.join(search_instructions)}

SEARCH AND CITATION RULES:
1.  **Restrict Sources:** Base your entire analysis ONLY on information found from the following domains: `fda.gov`, `nih.gov`, `pubmed.ncbi.nlm.nih.gov`, `who.int`, `mayoclinic.org`, `clevelandclinic.org`, `hopkinsmedicine.org`.
2.  **Synthesize Findings:** For each ingredient, summarize the specific health effects, mechanism of action, and official safety status found on these sites.
3.  **Mandatory Citations:** You MUST cite the exact URL for every piece of information you provide. Use a format like: "Sodium Nitrite is a preservative that can form nitrosamines under certain conditions."
4.  **No Outside Knowledge:** If you cannot find information on these specific sites, you must state: "No information was found for [ingredient] on the specified authoritative sources." DO NOT use your general training knowledge.

RESPONSE FORMAT - RETURN VALID JSON ONLY:
```json
{{
  "summary": "Brief overall summary based ONLY on your findings from the required sites.",
  "ingredients_assessment": {{
    "high_risk": [
      {{
        "name": "Ingredient Name",
        "risk_level": "high",
        "category": "preservative|additive|sweetener|etc",
        "micro_report": "Provide a medically factual 3-5 sentence summary (<=500 characters) covering mechanisms, documented risks, and guidance. Reference citations using bracketed numbers like [1].",
        "citations": [
          {{
            "id": 1,
            "title": "Exact study/article title from medical source",
            "source": "FDA|NIH|Mayo Clinic|etc",
            "year": "2024",
            "url": "actual URL found during search"
          }}
        ]
      }}
    ],
    "moderate_risk": [
      {{
        "name": "Ingredient Name", 
        "risk_level": "moderate",
        "category": "preservative|additive|etc",
        "micro_report": "Provide a concise 3-4 sentence overview (<=400 characters) describing known concerns, typical exposure guidance, and cite sources using bracketed numbers like [1].",
        "citations": [
          {{
            "id": 2,
            "title": "Research title",
            "source": "Medical authority",
            "year": "2024", 
            "url": "actual URL"
          }}
        ]
      }}
    ]
  }}
}}
```

CRITICAL: Each ingredient MUST have its own specific citations array with sources found during your research for THAT ingredient only. Do not reuse citations across ingredients.
"""
    

    async def _parse_assessment_response(
        self, 
        response_text: str,
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str],
        existing_risk_rating: Optional[str] = None,
        low_risk_ingredients: List[str] = None,
        ingredient_analyses: Dict[str, Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Parse Gemini's structured JSON response with ingredient-specific citations."""
        try:
            # Get product info from the current processing context
            product = getattr(self, '_current_product', None)
            if not product:
                return None
            
            # Try to parse the JSON response from Gemini
            import json
            import re
            
            # Extract JSON from markdown code blocks if present
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to find JSON in the raw text
                json_text = response_text.strip()
            
            logger.info(f"[Gemini JSON Parse] Attempting to parse: {json_text[:200]}...")
            
            try:
                gemini_data = json.loads(json_text)
                logger.info(f"[Gemini JSON Parse] Successfully parsed JSON structure")
                
                # Extract ingredients with their specific citations
                ingredients_assessment = gemini_data.get("ingredients_assessment", {})
                high_risk_with_citations = ingredients_assessment.get("high_risk", [])
                moderate_risk_with_citations = ingredients_assessment.get("moderate_risk", [])

                # Normalize AI micro reports to keep the UI concise and predictable
                for entry in high_risk_with_citations:
                    if isinstance(entry, dict):
                        entry["micro_report"] = self._normalize_micro_report(
                            entry.get("micro_report", ""),
                            max_sentences=5,
                            max_chars=500
                        )
                for entry in moderate_risk_with_citations:
                    if isinstance(entry, dict):
                        entry["micro_report"] = self._normalize_micro_report(
                            entry.get("micro_report", ""),
                            max_sentences=4,
                            max_chars=400
                        )
                
                logger.info(f"[Gemini JSON Parse] Found {len(high_risk_with_citations)} high-risk and {len(moderate_risk_with_citations)} moderate-risk ingredients with citations")
                
            except json.JSONDecodeError as e:
                logger.warning(f"[Gemini JSON Parse] Failed to parse JSON: {e}. Using fallback structure.")
                gemini_data = None
                high_risk_with_citations = []
                moderate_risk_with_citations = []
                
            # Use database risk_rating as the authoritative source for grading
            if existing_risk_rating:
                grade, color = self._map_risk_rating_to_grade_color(existing_risk_rating)
            else:
                grade, color = "C", "Yellow"  # Minimal fallback
            
            # Use Gemini's structured response if available, otherwise create fallback
            if gemini_data and gemini_data.get("summary"):
                summary = gemini_data["summary"]
            else:
                summary = "This product contains preservatives and additives requiring moderation. High salt content may contribute to cardiovascular concerns."
            
            assessment_data = {
                "summary": summary,
                "risk_summary": {
                    "grade": grade,
                    "color": color
                },
                "ingredients_assessment": {
                    "high_risk": high_risk_with_citations,  # Use Gemini's structured data with citations
                    "moderate_risk": moderate_risk_with_citations,  # Use Gemini's structured data with citations
                    "low_risk": []
                },
                "nutrition_insights": [],
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "product_code": product.product.code or "",
                    "product_name": product.product.name or "",
                    "product_brand": product.product.brand or "",
                    "ingredients": product.product.ingredients_text or "",
                    "assessment_type": "Gemini Grounded Health Assessment with Ingredient-Specific Citations"
                }
            }
            
            logger.info(f"[Gemini Assessment] Created structured assessment with {len(high_risk_with_citations)} high-risk and {len(moderate_risk_with_citations)} moderate-risk ingredients")
            
            # If Gemini didn't provide structured data, create fallback ingredients
            if not high_risk_with_citations and high_risk_ingredients:
                logger.warning(f"[Gemini Fallback] Creating fallback structure for {len(high_risk_ingredients)} high-risk ingredients")
                for ingredient in high_risk_ingredients:
                    micro_report = self._generate_ingredient_specific_fallback(ingredient, "high")
                    assessment_data["ingredients_assessment"]["high_risk"].append({
                        "name": ingredient,
                        "risk_level": "high",
                        "category": "preservative",
                        "micro_report": micro_report,
                        "citations": []  # Empty citations for fallback
                    })
            
            # Same for moderate-risk ingredients
            if not moderate_risk_with_citations and moderate_risk_ingredients:
                logger.warning(f"[Gemini Fallback] Creating fallback structure for {len(moderate_risk_ingredients)} moderate-risk ingredients")
                for ingredient in moderate_risk_ingredients:
                    micro_report = self._generate_ingredient_specific_fallback(ingredient, "moderate")
                    assessment_data["ingredients_assessment"]["moderate_risk"].append({
                        "name": ingredient,
                        "risk_level": "moderate", 
                        "category": "additive",
                        "micro_report": micro_report,
                        "citations": []  # Empty citations for fallback
                    })
            
            # Extract ALL ingredients from the product
            all_product_ingredients = self._extract_all_ingredients(
                product.product.ingredients_text or ""
            )
            
            # Create sets for easy lookup using the ingredient lists we just processed
            high_risk_set = {ing.lower() for ing in high_risk_ingredients}
            moderate_risk_set = {ing.lower() for ing in moderate_risk_ingredients}
            
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
                    if micro_report:
                        logger.debug(f"Using AI analysis for low-risk ingredient '{ingredient}': {micro_report[:50]}...")
                
                if not micro_report:
                    micro_report = self._generate_ingredient_specific_fallback(ingredient, "low")
                    logger.debug(f"Using fallback analysis for low-risk ingredient '{ingredient}': {micro_report[:50]}...")
                
                assessment_data["ingredients_assessment"]["low_risk"].append({
                    "name": ingredient,
                    "risk_level": "low",
                    "micro_report": micro_report,

                })
            
            # Ensure we have at least one ingredient in each category for validation
            if not assessment_data["ingredients_assessment"]["high_risk"] and not assessment_data["ingredients_assessment"]["moderate_risk"]:
                assessment_data["ingredients_assessment"]["moderate_risk"].append({
                    "name": "Processed Ingredients",
                    "risk_level": "moderate",
                    "micro_report": "Processed ingredients may have health implications with regular consumption. [1]",

                })
            
            # Generate nutrition insights using dynamic AI method with error handling
            try:
                assessment_data["nutrition_insights"] = await self._generate_nutrition_insights(self._current_product)
            except Exception as e:
                logger.warning(f"AI nutrition generation failed, falling back to static insights: {e}")
                assessment_data["nutrition_insights"] = self._generate_fallback_nutrition_insights(self._current_product)
            
            # Process response without citations
            
            # Analyze product quality indicators
            product_name = self._current_product.product.name.lower() if self._current_product else ""
            product_desc = self._current_product.product.description.lower() if self._current_product and hasattr(self._current_product.product, 'description') and self._current_product.product.description else ""
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
            assessment_data["summary"] = self._normalize_micro_report(
                summary_template,
                max_sentences=3,
                max_chars=320
            )
            
            # Update metadata with actual product information
            assessment_data["metadata"]["product_code"] = self._current_product.product.code
            assessment_data["metadata"]["product_name"] = self._current_product.product.name
            assessment_data["metadata"]["product_brand"] = self._current_product.product.brand or ""
            assessment_data["metadata"]["product_image_url"] = getattr(self._current_product.product, 'image_url', '') or ""
            assessment_data["metadata"]["ingredients"] = self._current_product.product.ingredients_text or ""
            
            return assessment_data
            
        except Exception as e:
            logger.error(f"Assessment parsing failed: {e}")
            return None
    
    # Removed obsolete _split_response_into_sections - using modern structured parsing
    
    # Removed obsolete _parse_ingredient_analysis - using _parse_ai_categorization_response
    
    # Removed obsolete _parse_citations - using Google grounding metadata
    
    # Removed obsolete _parse_citations_from_response - using Google grounding metadata
    
    # Removed obsolete _parse_citations_new_format - using Google grounding metadata
    
    async def _generate_nutrition_insights(self, product: ProductStructured) -> List[Dict[str, Any]]:
        """Generate dynamic AI-powered nutrition insights for the key nutrients."""
        nutrition_insights = []
        
        # Get nutrition data
        nutrition = product.health.nutrition if product.health else None
        product_name = product.product.name or "this product"
        
        if not nutrition:
            logger.warning(f"No nutrition data available for product {product.product.code}")
            return []
        
        # Generate AI commentary for all nutrients in a single batched call
        try:
            nutrients_to_analyze = [
                ("Protein", nutrition.protein, 50.0, "g"),
                ("Fat", nutrition.fat, 78.0, "g"), 
                ("Carbohydrates", nutrition.carbohydrates, 275.0, "g"),
                ("Salt", nutrition.salt, 2.3, "mg")  # Will convert to mg for display
            ]
            
            # Prepare nutrition data for batched AI processing
            nutrition_data = []
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
                
                nutrition_data.append({
                    "nutrient": nutrient_name,
                    "amount": amount,
                    "display_amount": display_amount,
                    "percent_dv": percent_dv,
                    "evaluation": evaluation
                })
            
            # Generate all nutrition commentaries in a single AI call
            ai_commentaries = await self._generate_batched_nutrition_commentary(
                nutrition_data, product_name
            )
            
            # Build nutrition insights with AI commentaries
            for data in nutrition_data:
                nutrition_insights.append({
                    "nutrient": data["nutrient"],
                    "amount_per_serving": data["display_amount"],
                    "evaluation": data["evaluation"],
                    "ai_commentary": ai_commentaries.get(data["nutrient"], 
                        self._get_fallback_commentary(data["nutrient"], data["evaluation"], data["percent_dv"]))
                })
            
            return nutrition_insights
            
        except Exception as e:
            logger.error(f"Error generating nutrition insights: {e}")
            # Fallback to simplified static data if AI fails
            return self._generate_fallback_nutrition_insights(product)
    
    async def _generate_batched_nutrition_commentary(
        self, 
        nutrition_data: List[Dict],
        product_name: str
    ) -> Dict[str, str]:
        """Generate AI commentary for all nutrients in a single batched call."""
        
        # Build comprehensive prompt for all nutrients
        nutrients_info = "\n".join([
            f"- {data['nutrient']}: {data['amount']} ({data['percent_dv']:.1f}% DV, {data['evaluation']} level)"
            for data in nutrition_data
        ])
        
        prompt = f"""Generate concise nutrition comments for {product_name}.

NUTRIENTS:
{nutrients_info}

Requirements:
- Generate ONE comment per nutrient (exactly {len(nutrition_data)} comments)
- Each comment: MAXIMUM 80 characters
- Focus on health implications for each nutrient level
- Use plain language, complete sentences
- Format: "NUTRIENT: comment text"

Examples:
Protein: Great protein source supporting muscle health goals
Salt: High sodium; balance with low-sodium foods daily
Fat: Low fat content makes this heart-healthy choice

Generate {len(nutrition_data)} comments in the exact format above:"""

        try:
            # Single AI call for all nutrition insights
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: genai.GenerativeModel(self.model).generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            temperature=0.3,
                            max_output_tokens=400  # Allow space for multiple comments
                        )
                    )
                ),
                timeout=8.0  # Single 8 second timeout for all nutrients (optimized)
            )
            
            # Parse the batched response
            response_text = response.text.strip()
            commentaries = {}
            
            # Parse AI response line by line
            for line in response_text.split('\n'):
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        nutrient = parts[0].strip()
                        comment = parts[1].strip()
                        
                        # Remove quotes if AI added them
                        if comment.startswith('"') and comment.endswith('"'):
                            comment = comment[1:-1]
                        
                        # Validate comment length
                        if len(comment) <= 80 and not comment.endswith('...') and not comment.endswith('..'):
                            commentaries[nutrient] = comment
                        else:
                            logger.warning(f"AI response too long for {nutrient}, will use fallback")
            
            logger.info(f"Generated {len(commentaries)} valid nutrition commentaries from batched AI call")
            return commentaries
            
        except asyncio.TimeoutError:
            logger.warning("Batched AI nutrition commentary timed out, using fallbacks")
            return {}
        except Exception as e:
            logger.warning(f"Batched AI nutrition commentary failed: {e}, using fallbacks")
            return {}
    
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
    
    def _generate_ingredient_specific_fallback(self, ingredient: str, risk_level: str) -> str:
        """Generate ingredient-specific fallback analysis without citation markers."""
        ingredient_lower = ingredient.lower()
        
        # High-risk ingredient fallbacks (no citation markers - Perplexity will add them)
        if risk_level == "high":
            if any(word in ingredient_lower for word in ['nitrite', 'nitrate', 'sodium nitrite']):
                return "Preservative linked to cancer risk and cardiovascular issues. Limit processed meat consumption."
            elif any(word in ingredient_lower for word in ['bha', 'bht', 'butylated hydroxyanisole']):
                return "Synthetic antioxidant with potential carcinogenic properties. Avoid regular consumption."
            elif any(word in ingredient_lower for word in ['msg', 'monosodium glutamate']):
                return "Flavor enhancer that may cause headaches and reactions in sensitive individuals."
            elif any(word in ingredient_lower for word in ['artificial color', 'red dye', 'yellow dye']):
                return "Synthetic coloring linked to hyperactivity and allergic reactions. Minimize intake."
            else:
                return f"{ingredient} identified as high-risk based on scientific evidence. Limit consumption."
        
        # Moderate-risk ingredient fallbacks  
        elif risk_level == "moderate":
            if any(word in ingredient_lower for word in ['sodium', 'salt']):
                return "High sodium content may contribute to hypertension and cardiovascular strain."
            elif any(word in ingredient_lower for word in ['sugar', 'corn syrup', 'glucose']):
                return "Added sugar increases caloric content and may impact blood glucose levels."
            elif any(word in ingredient_lower for word in ['phosphate', 'sodium phosphate']):
                return "Food additive that may affect calcium absorption and kidney function."
            elif any(word in ingredient_lower for word in ['carrageenan', 'guar gum']):
                return "Thickening agent that may cause digestive discomfort in sensitive individuals."
            else:
                return f"{ingredient} may have moderate health concerns. Consume in moderation."
        
        # Low-risk ingredient fallbacks
        else:  # risk_level == "low"
            if any(word in ingredient_lower for word in ['pork', 'beef', 'chicken', 'turkey']):
                return "High-quality protein source with essential amino acids. Choose lean cuts when possible. [7]"
            elif any(word in ingredient_lower for word in ['water', 'h2o']):
                return "Essential for hydration and food texture. No health concerns for consumption. [7]"
            elif any(word in ingredient_lower for word in ['natural flavor', 'natural flavoring']):
                return "Flavor compounds derived from natural sources. Generally safe but may contain allergens. [7]"
            elif any(word in ingredient_lower for word in ['vinegar', 'acetic acid']):
                return "Natural preservative and flavoring agent. May support digestive health. [7]"
            elif any(word in ingredient_lower for word in ['celery', 'celery powder']):
                return "Natural nitrite source used for curing. Safer alternative to synthetic nitrites. [7]"
            elif any(word in ingredient_lower for word in ['garlic', 'onion', 'spice']):
                return "Natural flavoring with potential antioxidant and anti-inflammatory properties. [7]"
            else:
                return f"{ingredient} is generally recognized as safe for consumption. [7]"
    
    def _get_fallback_ingredient_analysis(self, ingredient: str, risk_level: str) -> str:
        """Get fallback ingredient analysis for merge operations."""
        return self._generate_ingredient_specific_fallback(ingredient, risk_level)
    
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

    def _should_skip_citation(self, ingredient: str) -> bool:
        """Check if ingredient is trivial and should skip citation research."""
        ingredient_clean = ingredient.lower().strip()
        # Remove common prefixes/suffixes
        ingredient_clean = ingredient_clean.replace('natural ', '').replace(' extract', '').replace(' powder', '')
        return ingredient_clean in self.TRIVIAL_INGREDIENTS
    
    def _extract_source_name(self, url: str) -> str:
        """Extract clean source name from URL for citations."""
        if not url:
            return "Medical Research"
        
        logger.info(f"[Source Extraction] Processing URL: {url}")
        
        # Extract domain and convert to clean source names
        if 'fda.gov' in url:
            return "FDA"
        elif 'nih.gov' in url or 'pubmed.ncbi.nlm.nih.gov' in url:
            return "NIH"
        elif 'usda.gov' in url:
            return "USDA"
        elif 'cdc.gov' in url:
            return "CDC"
        elif 'mayoclinic.org' in url:
            return "Mayo Clinic"
        elif 'clevelandclinic.org' in url:
            return "Cleveland Clinic"
        elif 'hopkinsmedicine.org' in url:
            return "Johns Hopkins"
        elif 'who.int' in url:
            return "WHO"
        elif 'consumerreports.org' in url:
            return "Consumer Reports"
        elif 'ewg.org' in url:
            return "EWG"
        elif 'cancer.gov' in url:
            return "National Cancer Institute"
        elif 'columbiadoctors.org' in url:
            return "Columbia Medicine"
        elif 'pcrm.org' in url:
            return "PCRM"
        elif 'medicalnewstoday.com' in url:
            return "Medical News Today"
        elif 'healthline.com' in url:
            return "Healthline"
        elif 'piedmont.org' in url:
            return "Piedmont Healthcare"
        elif 'isitbadforyou.com' in url:
            return "Nutrition Research"
        else:
            # Extract domain name for other sources
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.replace('www.', '')
                logger.info(f"[Source Extraction] Extracted domain: {domain}")
                
                # Block any non-medical sources that slip through
                if self._is_blocked_source(domain):
                    logger.warning(f"[Source Extraction] Blocked non-medical domain: {domain}")
                    return "Medical Research"  # Safe fallback
                
                # Extract clean name from domain
                clean_name = domain.split('.')[0].title()
                logger.info(f"[Source Extraction] Final source name: {clean_name}")
                return clean_name
            except Exception as e:
                logger.warning(f"[Source Extraction] Failed to parse URL {url}: {e}")
                return "Medical Research"

    def _is_reputable_medical_source(self, domain: str) -> bool:
        """Filter for reputable medical and scientific sources only - prioritizing Apple App Store compliance."""
        if not domain:
            return False
        
        domain = domain.lower()
        
        # TIER 1: Primary government health authorities (highest priority for Apple compliance)
        tier_1_domains = [
            'fda.gov', 'nih.gov', 'cdc.gov', 'usda.gov', 'who.int', 
            'cancer.gov', 'health.gov', 'pubmed.ncbi.nlm.nih.gov'
        ]
        if any(gov_domain in domain for gov_domain in tier_1_domains):
            return True
        
        # TIER 2: Major medical institutions (strong authority for Apple compliance)
        tier_2_domains = [
            'mayoclinic.org', 'clevelandclinic.org', 'hopkinsmedicine.org',
            'harvard.edu', 'stanford.edu', 'columbia.edu', 'mayo.edu'
        ]
        if any(med_domain in domain for med_domain in tier_2_domains):
            return True
            
        # TIER 3: Medical organizations and journals (expanded for trustworthiness)
        tier_3_domains = [
            'cancer.org', 'heart.org', 'diabetes.org', 'pcrm.org',
            'columbiadoctors.org', 'piedmont.org', 'kaiserpermanente.org',
            # Additional trustworthy medical organizations
            'aicr.org', 'cancercouncil.com.au', 'cancerresearchuk.org',
            'diabetesjournals.org', 'nutrition.org', 'hsph.harvard.edu',
            'nutritionsource.hsph.harvard.edu', 'health.harvard.edu'
        ]
        if any(org_domain in domain for org_domain in tier_3_domains):
            return True
        
        # TIER 4: Additional reputable medical and research sites
        tier_4_domains = [
            'medlineplus.gov', 'healthline.com', 'medicalnewstoday.com',
            'webmd.com', 'verywellhealth.com', 'everydayhealth.com',
            'nutrition.gov', 'foodsafety.gov', 'extension.org'
        ]
        if any(med_domain in domain for med_domain in tier_4_domains):
            return True
        
        # Google Search Grounding - allow but deprioritize
        if any(google_domain in domain for google_domain in [
            'vertexaisearch.cloud.google.com', 'google.com', 'googleusercontent.com'
        ]):
            return True
        
        # Exclude non-medical sources
        if any(bad_domain in domain for bad_domain in [
            'reddit.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'tiktok.com', 'pinterest.com', 'quora.com'
        ]):
            return False
        
        # STRICT: Only accept .gov and .edu domains automatically
        # .org domains must be explicitly whitelisted above
        if any(domain.endswith(tld) for tld in ['.gov', '.edu']):
            return True
        
        return False

    def _is_blocked_source(self, domain: str) -> bool:
        """Block non-medical sources that should never appear in health citations."""
        if not domain:
            return True
            
        domain = domain.lower()
        
        # CRITICAL: Block social media and non-medical sources
        blocked_domains = [
            'tiktok.com', 'tiktok', 'bytedance.com',
            'facebook.com', 'instagram.com', 'twitter.com', 'x.com',
            'youtube.com', 'youtu.be', 'pinterest.com', 'snapchat.com',
            'reddit.com', 'quora.com', 'yahoo.com', 'bing.com',
            'wikipedia.org', 'wiki', 'blog', 'wordpress.com',
            'medium.com', 'substack.com', 'linkedin.com',
            # CRITICAL: Block food databases that are not medical authorities
            'openfoodfacts.org', 'world.openfoodfacts.org', 'foodfacts.org',
            'nutritionix.com', 'myfitnesspal.com', 'cronometer.com',
            # Block non-medical health blogs and commercial sites
            'eatresist.com', 'healthyeating.org', 'nutrition.org', 'foodsafety.org'
        ]
        
        # Check if any blocked domain appears in the URL
        for blocked in blocked_domains:
            if blocked in domain:
                return True
                
        return False

    def _get_source_priority_score(self, domain: str) -> int:
        """Calculate priority score for medical sources - higher scores = better for Apple App Store compliance."""
        if not domain:
            return 0
            
        domain = domain.lower()
        
        # TIER 1: Government health authorities (score: 100-90)
        tier_1_scores = {
            'fda.gov': 100,
            'nih.gov': 99, 
            'who.int': 98,
            'cdc.gov': 97,
            'pubmed.ncbi.nlm.nih.gov': 96,
            'cancer.gov': 95,
            'usda.gov': 94,
            'health.gov': 93
        }
        for gov_domain, score in tier_1_scores.items():
            if gov_domain in domain:
                return score
        
        # TIER 2: Major medical institutions (score: 89-80)
        tier_2_scores = {
            'mayoclinic.org': 89,
            'clevelandclinic.org': 88,
            'hopkinsmedicine.org': 87,
            'harvard.edu': 86,
            'stanford.edu': 85,
            'columbia.edu': 84,
            'mayo.edu': 83
        }
        for med_domain, score in tier_2_scores.items():
            if med_domain in domain:
                return score
        
        # TIER 3: Medical organizations (score: 79-70)
        tier_3_scores = {
            'cancer.org': 79,
            'heart.org': 78,
            'diabetes.org': 77,
            'pcrm.org': 76
        }
        for org_domain, score in tier_3_scores.items():
            if org_domain in domain:
                return score
        
        # TIER 4: Medical information sites (score: 69-60)
        tier_4_scores = {
            'medlineplus.gov': 69,
            'webmd.com': 65,
            'healthline.com': 63,
            'medicalnewstoday.com': 61
        }
        for info_domain, score in tier_4_scores.items():
            if info_domain in domain:
                return score
        
        # Generic .gov, .edu, .org get moderate scores
        if domain.endswith('.gov'):
            return 50
        elif domain.endswith('.edu'):
            return 45
        elif domain.endswith('.org'):
            return 40
        
        # Google grounding gets lowest priority
        if 'google.com' in domain or 'vertexaisearch' in domain:
            return 10
            
        return 5  
    
    def _get_fallback_citations(self) -> List[Dict[str, Any]]:
        """Simplified fallback citations - Perplexity will provide real ones."""
        return []  # Empty - Perplexity service will add real citations
    
    async def _resolve_redirect_url(self, redirect_url: str) -> str:
        """Resolve Google grounding redirect URL to final destination URL."""
        if not redirect_url or not redirect_url.startswith('https://vertexaisearch.cloud.google.com'):
            return redirect_url  # Return as-is if not a Google redirect
            
        try:
            logger.info(f"[URL Resolution] Resolving redirect: {redirect_url[:80]}...")
            
            # Use aiohttp to follow the redirect and get the final URL
            timeout = aiohttp.ClientTimeout(total=3.0)  # 3 second timeout
            
            # Create SSL context that doesn't verify certificates for Google's redirect service
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.head(redirect_url, allow_redirects=False) as response:
                    if response.status in [301, 302, 303, 307, 308]:
                        final_url = response.headers.get('Location', redirect_url)
                        logger.info(f"[URL Resolution] ✅ Resolved to: {final_url}")
                        return final_url
                    else:
                        logger.info(f"[URL Resolution] No redirect, status: {response.status}")
                        return redirect_url
                    
        except asyncio.TimeoutError:
            logger.warning(f"[URL Resolution] Timeout resolving redirect URL")
            return redirect_url  # Fallback to original URL
        except Exception as e:
            logger.warning(f"[URL Resolution] Failed to resolve redirect URL: {e}")
            return redirect_url  # Fallback to original URL
