"""Gemini MCP client for integrating with citation search tools."""
import logging
import asyncio
import os
from typing import List, Optional, Dict, Any
from contextlib import AsyncExitStack

from google import genai
from google.genai import types
from fastmcp.client.transports import FastMCPTransport
from fastmcp import Client as MCPClient

from app.services.citation_mcp_server import get_citation_server
from app.models.product import ProductStructured

logger = logging.getLogger(__name__)


class GeminiMCPService:
    """Service for using Gemini with MCP citation tools."""
    
    def __init__(self):
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-2.0-flash"
        self.mcp_server = get_citation_server()
        
    async def generate_health_assessment_with_citations(
        self, 
        product: ProductStructured,
        high_risk_ingredients: List[str]
    ) -> Dict[str, Any]:
        """
        Generate health assessment with real citations using MCP tools.
        
        Args:
            product: The product to analyze
            high_risk_ingredients: List of high-risk ingredients that need citations
            
        Returns:
            Dictionary containing assessment with real citations
        """
        try:
            # Set up MCP transport and client
            transport = FastMCPTransport(self.mcp_server)
            
            async with MCPClient(transport) as mcp_client:
                # Build the prompt for health assessment with citation requests
                prompt = self._build_citation_prompt(product, high_risk_ingredients)
                
                print(f"[Gemini MCP] Analyzing product: {product.product.name}")
                print(f"[Gemini MCP] High-risk ingredients to research: {high_risk_ingredients}")
                
                # Send request to Gemini with MCP tools available
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        tools=[mcp_client],  # Use MCP client as tool source
                    )
                )
                
                print(f"[Gemini MCP] Health assessment generated successfully")
                return {
                    "assessment": response.text,
                    "model_used": self.model,
                    "citations_included": True
                }
                
        except Exception as e:
            logger.error(f"Error in MCP health assessment: {e}")
            print(f"[Gemini MCP] Error: {e}")
            return {
                "error": str(e),
                "assessment": None,
                "citations_included": False
            }
    
    def _build_citation_prompt(self, product: ProductStructured, high_risk_ingredients: List[str]) -> str:
        """Build a prompt that requests citations for high-risk ingredients."""
        
        # Extract basic product info
        product_name = product.product.name
        ingredients_text = product.product.ingredients_text or "Ingredients not available"
        
        prompt = f"""You are a health assessment specialist analyzing meat products. 

PRODUCT TO ANALYZE:
Name: {product_name}
Ingredients: {ingredients_text}

HIGH-RISK INGREDIENTS IDENTIFIED: {', '.join(high_risk_ingredients)}

TASK:
For each high-risk ingredient listed above, you must:
1. Use the search_health_citations tool to find real scientific evidence about its health effects
2. Focus on specific health claims like "carcinogenic effects", "toxicity", "health risks", etc.
3. Include the actual citations in your response

IMPORTANT INSTRUCTIONS:
- You MUST use the search_health_citations tool for each high-risk ingredient
- Do NOT make up any citations or references
- Only include citations that you obtained from the search tool
- Provide a balanced health assessment based on the real scientific evidence found

Please provide a comprehensive health assessment for this product with proper scientific citations."""

        return prompt
    
    async def test_mcp_integration(self) -> Dict[str, Any]:
        """Test the MCP integration with a simple query."""
        try:
            transport = FastMCPTransport(self.mcp_server)
            
            async with MCPClient(transport) as mcp_client:
                prompt = """Test the citation search by finding scientific evidence about BHA and its carcinogenic effects. 
                Use the search_health_citations tool to find real studies."""
                
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0,
                        tools=[mcp_client],
                    )
                )
                
                return {
                    "success": True,
                    "response": response.text,
                    "model": self.model
                }
                
        except Exception as e:
            logger.error(f"MCP integration test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Test the MCP integration
async def test_gemini_mcp():
    """Test function for Gemini MCP integration."""
    service = GeminiMCPService()
    
    print("Testing Gemini MCP Integration...")
    result = await service.test_mcp_integration()
    
    if result.get("success"):
        print("✅ MCP Integration Test Successful!")
        print("Response:")
        print(result["response"])
    else:
        print("❌ MCP Integration Test Failed!")
        print(f"Error: {result.get('error')}")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_gemini_mcp()) 