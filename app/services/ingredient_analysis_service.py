"""Service for analyzing individual ingredients with AI-generated health information and citations."""
import logging
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
        self.gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL or 'gemini-2.0-flash')
        
        # Use singleton Perplexity citation service
        self.citation_service = get_citation_service()
        
        logger.info("IngredientAnalysisService initialized")
    
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
            
            # Step 2: Get risk level to determine if citations are needed
            risk_level = analysis.get("risk_level", "unknown")
            
            # Step 3: Get Perplexity citations if needed
            citations = []
            if self.citation_service.should_get_citations(ingredient_name, risk_level):
                logger.info(f"[Ingredient Analysis] Getting citations for {risk_level}-risk ingredient")
                citations_map = await self.citation_service.get_citations_for_ingredients([ingredient_name])
                citations = citations_map.get(ingredient_name, [])
            else:
                logger.info(f"[Ingredient Analysis] Skipping citations for {risk_level}-risk ingredient")
            
            # Step 4: Combine results
            result = {
                "ingredient": ingredient_name,
                "analysis": analysis.get("analysis", ""),
                "risk_level": risk_level,
                "primary_concern": analysis.get("primary_concern", ""),
                "mechanism": analysis.get("mechanism", ""),
                "recommendations": analysis.get("recommendations", ""),
                "citations": citations,
                "metadata": {
                    "ai_model": "gemini-pro",
                    "citation_source": "perplexity-ai" if citations else "none"
                }
            }
            
            logger.info(f"[Ingredient Analysis] Complete: {risk_level} risk, {len(citations)} citations")
            return result
            
        except Exception as e:
            logger.error(f"[Ingredient Analysis] Failed for {ingredient_name}: {e}")
            return {
                "error": f"Failed to analyze ingredient: {str(e)}",
                "ingredient": ingredient_name
            }
    
    async def _generate_ingredient_analysis(self, ingredient_name: str) -> Dict[str, Any]:
        """Generate AI analysis for the ingredient using Gemini."""
        
        prompt = f"""Analyze the food ingredient "{ingredient_name}" for health effects.

Provide a comprehensive analysis covering:
1. Risk level (high, moderate, low)
2. Primary health concerns (if any)
3. Biological mechanism of action
4. Consumption recommendations

Format your response as a detailed analysis suitable for health-conscious consumers.
Focus on evidence-based information about safety, side effects, and health implications.

Ingredient: {ingredient_name}

Respond in this format:
RISK_LEVEL: [high/moderate/low]
PRIMARY_CONCERN: [Brief concern or "Generally recognized as safe"]
MECHANISM: [How it affects the body]
ANALYSIS: [2-3 paragraph detailed analysis]
RECOMMENDATIONS: [Consumption advice]"""

        try:
            logger.info(f"[Gemini Analysis] Generating analysis for: {ingredient_name}")
            
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=800
                )
            )
            
            if not response.text:
                logger.warning(f"[Gemini Analysis] Empty response for {ingredient_name}")
                return {"error": "No analysis generated"}
            
            # Parse the structured response
            return self._parse_analysis_response(response.text)
            
        except Exception as e:
            logger.error(f"[Gemini Analysis] Error for {ingredient_name}: {e}")
            return {"error": f"AI analysis failed: {str(e)}"}
    
    def _parse_analysis_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the structured Gemini response into components."""
        
        try:
            lines = response_text.strip().split('\n')
            result = {
                "risk_level": "unknown",
                "primary_concern": "",
                "mechanism": "",
                "analysis": "",
                "recommendations": ""
            }
            
            current_section = None
            content_lines = []
            
            for line in lines:
                line = line.strip()
                
                if line.startswith("RISK_LEVEL:"):
                    result["risk_level"] = line.replace("RISK_LEVEL:", "").strip().lower()
                elif line.startswith("PRIMARY_CONCERN:"):
                    result["primary_concern"] = line.replace("PRIMARY_CONCERN:", "").strip()
                elif line.startswith("MECHANISM:"):
                    result["mechanism"] = line.replace("MECHANISM:", "").strip()
                elif line.startswith("ANALYSIS:"):
                    current_section = "analysis"
                    content = line.replace("ANALYSIS:", "").strip()
                    if content:
                        content_lines = [content]
                    else:
                        content_lines = []
                elif line.startswith("RECOMMENDATIONS:"):
                    # Save previous section
                    if current_section == "analysis" and content_lines:
                        result["analysis"] = " ".join(content_lines)
                    
                    current_section = "recommendations"
                    content = line.replace("RECOMMENDATIONS:", "").strip()
                    if content:
                        content_lines = [content]
                    else:
                        content_lines = []
                elif current_section and line:
                    content_lines.append(line)
            
            # Save final section
            if current_section == "recommendations" and content_lines:
                result["recommendations"] = " ".join(content_lines)
            elif current_section == "analysis" and content_lines:
                result["analysis"] = " ".join(content_lines)
            
            # Fallback: if parsing fails, use entire response as analysis
            if not result["analysis"]:
                result["analysis"] = response_text
                
            return result
            
        except Exception as e:
            logger.error(f"[Analysis Parsing] Error: {e}")
            return {
                "analysis": response_text,
                "risk_level": "unknown",
                "primary_concern": "Requires further review",
                "mechanism": "",
                "recommendations": "Consult healthcare professionals for advice"
            }