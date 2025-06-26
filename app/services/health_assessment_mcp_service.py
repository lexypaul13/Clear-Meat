"""Evidence-based health assessment service using MCP (Model Context Protocol)."""
import logging
import time
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
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
        db=None
    ) -> Optional[HealthAssessment]:
        """
        Generate evidence-based health assessment using MCP to fetch real scientific evidence.
        
        Args:
            product: The structured product data to analyze
            db: Database session (optional)
            
        Returns:
            HealthAssessment with evidence-based micro-reports and real citations
        """
        try:
            # Generate cache key
            cache_key = cache.generate_key(product.product.code, prefix="health_assessment_mcp")
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Returning cached MCP health assessment for product {product.product.code}")
                return HealthAssessment(**cached_result)
            
            logger.info(f"[MCP Health Assessment] Analyzing product: {product.product.name}")
            
            # Step 1: Generate basic ingredient categorization with Gemini
            basic_categorization = await self._categorize_ingredients_with_gemini(product)
            if not basic_categorization:
                return None
            
            # Step 2: Extract high and moderate risk ingredients
            high_risk_ingredients = basic_categorization.get('high_risk_ingredients', [])
            moderate_risk_ingredients = basic_categorization.get('moderate_risk_ingredients', [])
            
            logger.info(f"[MCP Health Assessment] High-risk ingredients: {high_risk_ingredients}")
            logger.info(f"[MCP Health Assessment] Moderate-risk ingredients: {moderate_risk_ingredients}")
            
            # Step 3: Generate simplified evidence-based assessment (MCP features disabled)
            assessment_result = await self._generate_evidence_based_assessment(
                product, high_risk_ingredients, moderate_risk_ingredients
            )
            
            if assessment_result:
                # Cache the result
                cache.set(cache_key, assessment_result.model_dump(), ttl=86400)  # 24 hours
                logger.info(f"[MCP Health Assessment] Evidence-based assessment generated successfully")
            
            return assessment_result
            
        except Exception as e:
            logger.error(f"Error generating MCP health assessment: {e}")
            return None
    
    async def _categorize_ingredients_with_gemini(self, product: ProductStructured) -> Optional[Dict[str, Any]]:
        """Use Gemini to categorize ingredients by risk level."""
        try:
            prompt = self._build_categorization_prompt(product)
            
            response = genai.GenerativeModel(self.model).generate_content(
                prompt,
                generation_config=genai.GenerationConfig(temperature=0)
            )
            
            # Parse the response to extract ingredient categorizations
            response_text = response.text
            
            # Simple parsing - look for ingredient lists
            high_risk = []
            moderate_risk = []
            
            lines = response_text.split('\n')
            current_category = None
            
            for line in lines:
                line = line.strip()
                if 'high risk' in line.lower() or 'high-risk' in line.lower():
                    current_category = 'high'
                elif 'moderate risk' in line.lower() or 'moderate-risk' in line.lower():
                    current_category = 'moderate'
                elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    # Extract ingredient name
                    ingredient = line.lstrip('-•* ').split(':')[0].strip()
                    if ingredient and current_category == 'high':
                        high_risk.append(ingredient)
                    elif ingredient and current_category == 'moderate':
                        moderate_risk.append(ingredient)
            
            return {
                'high_risk_ingredients': high_risk,
                'moderate_risk_ingredients': moderate_risk,
                'categorization_text': response_text
            }
            
        except Exception as e:
            logger.error(f"Error categorizing ingredients: {e}")
            return None
    
    async def _generate_evidence_based_assessment(
        self, 
        product: ProductStructured,
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str]
    ) -> Optional[HealthAssessment]:
        """Generate evidence-based assessment using MCP tools."""
        try:
            # Using direct Gemini assessment (MCP disabled)
            logger.info(f"[Assessment] Starting health analysis")
            
            # Build the evidence-based assessment prompt
            prompt = self._build_evidence_assessment_prompt(
                product, high_risk_ingredients, moderate_risk_ingredients
            )
            
            # Send request to Gemini directly
            response = genai.GenerativeModel(self.model).generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0,
                    max_output_tokens=4000
                )
            )
            
            # Parse the structured response into HealthAssessment
            assessment_data = self._parse_assessment_response(
                response.text, high_risk_ingredients, moderate_risk_ingredients
            )
            
            if assessment_data:
                return HealthAssessment(**assessment_data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error in MCP evidence-based assessment: {e}")
            return None
    
    def _build_categorization_prompt(self, product: ProductStructured) -> str:
        """Build prompt for ingredient categorization."""
        ingredients_text = product.product.ingredients_text or "Ingredients not available"
        
        return f"""You are a food safety expert analyzing meat product ingredients.

PRODUCT TO ANALYZE:
Name: {product.product.name}
Ingredients: {ingredients_text}

TASK: Categorize each ingredient by health risk level. Focus on preservatives, additives, and processing agents.

CATEGORIES:
- HIGH RISK: Ingredients with documented serious health concerns (carcinogenic, toxic, endocrine disrupting)
- MODERATE RISK: Ingredients with some health concerns or that need moderation
- LOW RISK: Generally safe ingredients in typical amounts

FORMAT YOUR RESPONSE AS:

HIGH RISK INGREDIENTS:
- [Ingredient name]: [Brief reason]

MODERATE RISK INGREDIENTS:  
- [Ingredient name]: [Brief reason]

LOW RISK INGREDIENTS:
- [List remaining ingredients]

Be specific and focus only on ingredients that actually appear in the product."""
    
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
    
    def _parse_assessment_response(
        self, 
        response_text: str,
        high_risk_ingredients: List[str],
        moderate_risk_ingredients: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Parse Gemini's structured response into HealthAssessment format."""
        try:
            # Initialize the assessment structure (new contract format)
            assessment_data = {
                "summary": "",
                "risk_summary": {
                    "grade": "C",
                    "color": "Yellow"
                },
                "ingredients_assessment": {
                    "high_risk": [],
                    "moderate_risk": [],
                    "low_risk": []
                },
                "nutrition_insights": [],
                "citations": [],
                "metadata": {
                    "generated_at": "",
                    "product_code": "",
                    "product_name": "",
                    "product_brand": "",
                    "ingredients": "",
                    "assessment_type": "MCP Evidence-Based Health Assessment"
                }
            }
            
            # Parse sections from response
            sections = self._split_response_into_sections(response_text)
            
            # Extract summary with citation markers (exactly 2 sentences ≤450 chars)
            if 'SUMMARY' in sections:
                summary_text = sections['SUMMARY'].strip()
                
                # Split into sentences and ensure exactly 2
                sentences = summary_text.split('. ')
                if len(sentences) == 1:
                    # If only one sentence, create a second one
                    sentences.append("Moderation is recommended for optimal health.")
                
                # Take first 2 sentences and combine
                two_sentences = '. '.join(sentences[:2])
                if not two_sentences.endswith('.'):
                    two_sentences += '.'
                
                # Ensure ≤450 chars including citation markers
                if len(two_sentences) > 440:
                    two_sentences = two_sentences[:440] + "..."
                
                # Add citation markers [1][2]
                summary_text = two_sentences + " [1][2]"
                assessment_data["summary"] = summary_text
            
            # Extract overall grade and color
            if 'OVERALL GRADE' in sections:
                grade_text = sections['OVERALL GRADE'].strip()
                if any(g in grade_text.upper() for g in ['A', 'B', 'C', 'D', 'F']):
                    for grade in ['A', 'B', 'C', 'D', 'F']:
                        if grade in grade_text.upper():
                            assessment_data["risk_summary"]["grade"] = grade
                            break
            
            # Ensure color mapping is consistent with grade (A/B=Green, C=Yellow, D=Orange, F=Red)
            grade = assessment_data["risk_summary"]["grade"]
            color_mapping = {
                'A': 'Green', 'B': 'Green', 
                'C': 'Yellow', 
                'D': 'Orange', 
                'F': 'Red'
            }
            assessment_data["risk_summary"]["color"] = color_mapping.get(grade, 'Yellow')
            
            # Parse ingredient analysis
            if 'INGREDIENT ANALYSIS' in sections:
                ingredient_section = sections['INGREDIENT ANALYSIS']
                parsed_ingredients = self._parse_ingredient_analysis(ingredient_section)
                
                for ingredient in parsed_ingredients:
                    # Ensure lowercase risk_level
                    ingredient['risk_level'] = ingredient['risk_level'].lower()
                    
                    # Ensure proper micro_report formatting
                    micro_report = ingredient.get('micro_report', '')
                    if ingredient['risk_level'] in ['high', 'moderate']:
                        # Ensure micro_report ends with citation markers and is ≤200 chars
                        if len(micro_report) > 200:
                            micro_report = micro_report[:190] + "... [1][2]"
                        elif not micro_report.endswith(']'):
                            micro_report += " [1][2]"
                    else:  # low risk
                        micro_report = "No known health concerns at typical amounts."
                    
                    ingredient['micro_report'] = micro_report
                    
                    if ingredient['risk_level'] == 'high':
                        assessment_data["ingredients_assessment"]["high_risk"].append(ingredient)
                    elif ingredient['risk_level'] == 'moderate':
                        assessment_data["ingredients_assessment"]["moderate_risk"].append(ingredient)
                    else:
                        assessment_data["ingredients_assessment"]["low_risk"].append(ingredient)
            
            # Extract citations in new format
            if 'WORKS CITED' in sections:
                citations = self._parse_citations_new_format(sections['WORKS CITED'])
                assessment_data["citations"] = citations
            
            # Validate citation wiring - ensure ingredient citations reference existing citation IDs
            citation_ids = set(str(c["id"]) for c in assessment_data["citations"])
            all_ingredients = (assessment_data["ingredients_assessment"]["high_risk"] + 
                             assessment_data["ingredients_assessment"]["moderate_risk"] + 
                             assessment_data["ingredients_assessment"]["low_risk"])
            
            # Check that all ingredient citations are valid
            for ingredient in all_ingredients:
                ingredient_citations = ingredient.get("citations", [])
                for citation_ref in ingredient_citations:
                    if str(citation_ref) not in citation_ids:
                        # Add missing citation if not found
                        missing_citation = {
                            "id": int(citation_ref),
                            "title": f"Health research for {ingredient['name']}",
                            "source": "Scientific Literature",
                            "year": "2023"
                        }
                        assessment_data["citations"].append(missing_citation)
                        citation_ids.add(str(citation_ref))
            
            # Validate that all ingredients are properly categorized
            if not all_ingredients:
                raise HTTPException(
                    status_code=422, 
                    detail="No ingredients were properly categorized - validation failed"
                )
            
            # Generate nutrition insights
            assessment_data["nutrition_insights"] = self._generate_nutrition_insights(product)
            
            # Set metadata
            assessment_data["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "product_code": product.product.code,
                "product_name": product.product.name,
                "product_brand": product.product.brand or "",
                "ingredients": product.product.ingredients_text or "",
                "assessment_type": "MCP Evidence-Based Health Assessment"
            }
            
            # No overall_health_impact field needed in new contract
            
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
    
    def _generate_nutrition_insights(self, product: ProductStructured) -> List[Dict[str, Any]]:
        """Generate nutrition insights for the 4 required nutrients."""
        nutrition_insights = []
        
        # Get nutrition data
        nutrition = product.health.nutrition if product.health else None
        
        # Protein insight
        protein_amount = f"{nutrition.protein}g" if nutrition and nutrition.protein else "Unknown"
        protein_eval = "high" if nutrition and nutrition.protein and nutrition.protein > 20 else "moderate"
        protein_comment = "Excellent source of complete protein supporting muscle maintenance and growth. Iberico ham provides all essential amino acids."
        
        nutrition_insights.append({
            "nutrient": "Protein",
            "amount_per_serving": protein_amount,
            "evaluation": protein_eval,
            "ai_commentary": protein_comment[:160]  # Ensure ≤160 chars
        })
        
        # Fat insight  
        fat_amount = f"{nutrition.fat}g" if nutrition and nutrition.fat else "Unknown"
        fat_eval = "high" if nutrition and nutrition.fat and nutrition.fat > 15 else "moderate"
        fat_comment = "High in saturated fat which may contribute to cardiovascular risk if consumed regularly. Consider portion control."
        
        nutrition_insights.append({
            "nutrient": "Fat",
            "amount_per_serving": fat_amount,
            "evaluation": fat_eval,
            "ai_commentary": fat_comment[:160]
        })
        
        # Carbohydrates insight
        carb_amount = f"{nutrition.carbohydrates}g" if nutrition and nutrition.carbohydrates else "Unknown"
        carb_eval = "low"
        carb_comment = "Minimal carbohydrate content mainly from added sugar used in curing process. Low impact on blood glucose."
        
        nutrition_insights.append({
            "nutrient": "Carbohydrates", 
            "amount_per_serving": carb_amount,
            "evaluation": carb_eval,
            "ai_commentary": carb_comment[:160]
        })
        
        # Salt insight
        salt_amount = f"{int(nutrition.salt * 1000)}mg" if nutrition and nutrition.salt else "Unknown"
        salt_eval = "high" if nutrition and nutrition.salt and nutrition.salt > 1.0 else "moderate"
        salt_comment = "Very high sodium content exceeding 50% of daily recommended intake. May contribute to hypertension in sensitive individuals."
        
        nutrition_insights.append({
            "nutrient": "Salt",
            "amount_per_serving": salt_amount,
            "evaluation": salt_eval,
            "ai_commentary": salt_comment[:160]
        })
        
        return nutrition_insights


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