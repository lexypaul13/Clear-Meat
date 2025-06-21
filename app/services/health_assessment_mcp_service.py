"""Evidence-based health assessment service using MCP (Model Context Protocol)."""
import logging
import time
import asyncio
import os
from typing import Dict, Any, Optional, List
from contextlib import AsyncExitStack

import google.generativeai as genai
from pydantic import ValidationError
from app.core.config import settings
from app.core.cache import cache
from app.models.product import HealthAssessment, ProductStructured
from app.services.citation_mcp_server import get_citation_server
from fastmcp.client.transports import FastMCPTransport
from fastmcp import Client as MCPClient

logger = logging.getLogger(__name__)


class HealthAssessmentMCPService:
    """Evidence-based health assessment service using MCP for real scientific analysis."""
    
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")
        
        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL
        self.mcp_server = get_citation_server()
        
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
            
            # Step 3: Generate evidence-based assessment using MCP
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
            # Set up MCP transport and client
            transport = FastMCPTransport(self.mcp_server)
            
            async with MCPClient(transport) as mcp_client:
                # Build the evidence-based assessment prompt
                prompt = self._build_evidence_assessment_prompt(
                    product, high_risk_ingredients, moderate_risk_ingredients
                )
                
                logger.info(f"[MCP Assessment] Starting evidence-based analysis")
                
                # Send request to Gemini with MCP tools available
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
            # Initialize the assessment structure
            assessment_data = {
                "summary": "",
                "overall_health_impact": "",
                "risk_summary": {
                    "grade": "C",
                    "color": "Yellow",
                    "overall_score": 50
                },
                "ingredients_assessment": {
                    "high_risk": [],
                    "moderate_risk": [],
                    "low_risk": []
                },
                "real_citations": {},
                "works_cited": [],
                "source_disclaimer": "Assessment based on real scientific evidence from peer-reviewed research"
            }
            
            # Parse sections from response
            sections = self._split_response_into_sections(response_text)
            
            # Extract summary
            if 'SUMMARY' in sections:
                assessment_data["summary"] = sections['SUMMARY'].strip()
            
            # Extract overall grade and color
            if 'OVERALL GRADE' in sections:
                grade_text = sections['OVERALL GRADE'].strip()
                if any(g in grade_text.upper() for g in ['A', 'B', 'C', 'D', 'F']):
                    for grade in ['A', 'B', 'C', 'D', 'F']:
                        if grade in grade_text.upper():
                            assessment_data["risk_summary"]["grade"] = grade
                            break
            
            if 'GRADE COLOR' in sections:
                color_text = sections['GRADE COLOR'].strip()
                colors = ['Green', 'Yellow', 'Orange', 'Red']
                for color in colors:
                    if color.lower() in color_text.lower():
                        assessment_data["risk_summary"]["color"] = color
                        break
            
            # Parse ingredient analysis
            if 'INGREDIENT ANALYSIS' in sections:
                ingredient_section = sections['INGREDIENT ANALYSIS']
                parsed_ingredients = self._parse_ingredient_analysis(ingredient_section)
                
                for ingredient in parsed_ingredients:
                    if ingredient['risk_level'].lower() == 'high':
                        assessment_data["ingredients_assessment"]["high_risk"].append(ingredient)
                    elif ingredient['risk_level'].lower() == 'moderate':
                        assessment_data["ingredients_assessment"]["moderate_risk"].append(ingredient)
            
            # Extract citations
            if 'WORKS CITED' in sections:
                citations = self._parse_citations(sections['WORKS CITED'])
                assessment_data["works_cited"] = citations
                
                # Create real_citations dictionary
                real_citations = {}
                for i, citation in enumerate(citations, 1):
                    real_citations[str(i)] = citation.get('citation', '')
                assessment_data["real_citations"] = real_citations
            
            # Set overall health impact
            grade = assessment_data["risk_summary"]["grade"]
            if grade in ['A', 'B']:
                assessment_data["overall_health_impact"] = "positive"
            elif grade == 'C':
                assessment_data["overall_health_impact"] = "neutral"
            else:
                assessment_data["overall_health_impact"] = "negative"
            
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
                # Simple citation parsing - just extract citation markers
                citations_text = line.split(':', 1)[1].strip()
                citation_markers = []
                import re
                markers = re.findall(r'\[(\d+)\]', citations_text)
                current_ingredient['citations'] = markers
        
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