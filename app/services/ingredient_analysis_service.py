"""Service for analyzing individual ingredients with AI-generated health information and citations."""
import logging
import re
from typing import Dict, Any
import google.generativeai as genai
from app.core.config import settings
from app.services.perplexity_citation_service import get_citation_service

logger = logging.getLogger(__name__)


class IngredientAnalysisService:
    """Service for comprehensive individual ingredient analysis with citations."""
    
    def __init__(self):
        """Initialize the ingredient analysis service."""
        # Initialize Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        # Model fallback chain: primary -> fallback -> emergency
        self.model_chain = [
            settings.GEMINI_MODEL or 'gemini-2.0-flash',
            'gemini-2.0-flash-001',
            'gemini-flash-latest'
        ]
        
        # Initialize with primary model
        self.gemini_model = genai.GenerativeModel(self.model_chain[0])
        self.current_model = self.model_chain[0]
        
        # Use singleton Perplexity citation service
        self.citation_service = get_citation_service()
        
        logger.info(f"IngredientAnalysisService initialized with model: {self.current_model}")
    
    async def analyze_ingredient(self, ingredient_name: str) -> Dict[str, Any]:
        """
        Generate comprehensive analysis for a single ingredient.
        
        Args:
            ingredient_name: Name of the ingredient to analyze
            
        Returns:
            Dict containing analysis, risk level, and citations
        """
        logger.info(f"[Ingredient Analysis] Starting analysis for: {ingredient_name}")
        
        try:
            # Step 1: Generate Gemini health analysis
            analysis = await self._generate_ingredient_analysis(ingredient_name)
            
            if "error" in analysis:
                return analysis
            
            # Step 2: Extract risk level from analysis text to determine if citations are needed
            analysis_text = analysis.get("analysis", "").lower()
            if ("high risk" in analysis_text or "dangerous" in analysis_text or 
                "carcinogenic" in analysis_text or "toxic" in analysis_text):
                risk_level = "high"
            elif ("moderate risk" in analysis_text or "concern" in analysis_text or 
                  "caution" in analysis_text or "cancer" in analysis_text or
                  "carcinogenic compounds" in analysis_text or "increased risk" in analysis_text or
                  "elevates" in analysis_text or "cardiovascular disease" in analysis_text or
                  "blood pressure" in analysis_text or "stroke" in analysis_text or
                  "hypertension" in analysis_text or "kidney disease" in analysis_text or
                  "sensitive individuals" in analysis_text or "limit" in analysis_text):
                risk_level = "moderate"
            else:
                risk_level = "low"
            
            # Step 3: Get Perplexity citations if needed
            citations = []
            if self.citation_service.should_get_citations(ingredient_name, risk_level):
                logger.info(f"[Ingredient Analysis] Getting citations for {risk_level}-risk ingredient")
                citations_map = await self.citation_service.get_citations_for_ingredients([ingredient_name])
                citations = citations_map.get(ingredient_name, [])
            else:
                logger.info(f"[Ingredient Analysis] Skipping citations for {risk_level}-risk ingredient")
            
            # Step 4: Combine results (simplified response)
            result = {
                "ingredient": ingredient_name,
                "analysis": analysis.get("analysis", ""),
                "citations": citations,
                "metadata": {
                    "ai_model": "gemini-pro",
                    "citation_source": "perplexity-ai" if citations else "none"
                }
            }
            
            logger.info(f"[Ingredient Analysis] Complete: {len(citations)} citations")
            return result
            
        except Exception as e:
            logger.error(f"[Ingredient Analysis] Failed for {ingredient_name}: {e}")
            return {
                "error": f"Failed to analyze ingredient: {str(e)}",
                "ingredient": ingredient_name
            }
    
    async def _generate_ingredient_analysis(self, ingredient_name: str) -> Dict[str, Any]:
        """Generate AI analysis for the ingredient using Gemini with fallback models."""
        
        prompt = f"""Analyze the food ingredient "{ingredient_name}" for health effects.

Provide a concise, evidence-based briefing suitable for health-conscious consumers.

Ingredient: {ingredient_name}

RESPONSE REQUIREMENTS:
1. Write exactly 3-5 sentences (max 550 characters) summarizing safety profile, key mechanisms, primary health risks, vulnerable populations, and consumption guidance.
2. Mention authoritative sources inline when relevant (e.g., FDA, EFSA) but do NOT include bracketed citation numbers.
3. Maintain a neutral, factual tone and avoid marketing language.

FORMAT:
ANALYSIS: Sentence 1. Sentence 2. Sentence 3. (Optionally Sentence 4-5.)"""

        # Try each model in the fallback chain
        for model_index, model_name in enumerate(self.model_chain):
            try:
                logger.info(f"[Gemini Analysis] Attempting with model {model_name} for: {ingredient_name}")
                
                # Create model instance for this attempt
                current_model = genai.GenerativeModel(model_name)
                
                response = current_model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=800
                    )
                )
                
                if not response.text:
                    logger.warning(f"[Gemini Analysis] Empty response from {model_name} for {ingredient_name}")
                    if model_index < len(self.model_chain) - 1:
                        continue  # Try next model
                    return {"error": "No analysis generated"}
                
                # Success - update current model and log
                if model_name != self.current_model:
                    logger.info(f"[Gemini Analysis] Switched to fallback model: {model_name}")
                    self.current_model = model_name
                    self.gemini_model = current_model
                
                # Parse the structured response
                return self._parse_analysis_response(response.text)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[Gemini Analysis] Model {model_name} failed for {ingredient_name}: {error_msg}")
                
                # Check if it's a model not found error
                if "not found" in error_msg.lower() or "not supported" in error_msg.lower():
                    if model_index < len(self.model_chain) - 1:
                        logger.info(f"[Gemini Analysis] Model {model_name} not available, trying next model")
                        continue  # Try next model in chain
                
                # If this is the last model or non-model error, return error
                if model_index == len(self.model_chain) - 1:
                    return {"error": f"AI analysis failed with all models: {error_msg}"}
        
        # Should never reach here, but safety fallback
        return {"error": "AI analysis failed: All models unavailable"}
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the structured Gemini response into components."""
        
        try:
            lines = response_text.strip().split('\n')
            result = {
                "analysis": ""
            }
            
            current_section = None
            content_lines = []
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("ANALYSIS:"):
                    current_section = "analysis"
                    content = line.replace("ANALYSIS:", "").strip()
                    if content:
                        content_lines = [content]
                    else:
                        content_lines = []
                elif current_section == "analysis" and line:
                    content_lines.append(line)
            
            # Save final section
            if current_section == "analysis" and content_lines:
                result["analysis"] = self._normalize_analysis_text(" ".join(content_lines))
            
            # Fallback: if parsing fails, use entire response as analysis
            if not result["analysis"]:
                result["analysis"] = self._normalize_analysis_text(response_text)
                
            return result
            
        except Exception as e:
            logger.error(f"[Analysis Parsing] Error: {e}")
            return {
                "analysis": self._normalize_analysis_text(response_text),
                "risk_level": "unknown",
                "primary_concern": "Requires further review",
                "mechanism": "",
                "recommendations": "Consult healthcare professionals for advice"
            }

    def _normalize_analysis_text(self, text: str) -> str:
        """Clamp AI analysis text to 3-5 sentences and target length."""
        if not text:
            return ""

        normalized = re.sub(r'\s+', ' ', text).strip()
        if not normalized:
            return ""

        sentences = re.split(r'(?<=[.!?])\s+', normalized)
        trimmed = sentences[:5]
        normalized = ' '.join(trimmed).strip()
        normalized = re.sub('\\[\\d+\\]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        max_chars = 550
        if len(normalized) > max_chars:
            normalized = normalized[:max_chars].rstrip(' ,;') + '…'

        return normalized
