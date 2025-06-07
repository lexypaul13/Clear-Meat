"""MCP server for citation search tools using FastMCP."""
import logging
import asyncio
from typing import Dict, Any
from fastmcp import FastMCP

from app.services.citation_tools import CitationSearchService
from app.models.citation import CitationSearch

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp_server = FastMCP("clear-meat-citations")

# Initialize citation service
citation_service = CitationSearchService()

@mcp_server.tool()
def search_health_citations(ingredient: str, health_claim: str, max_results: int = 3) -> str:
    """
    Search for real scientific citations about ingredient health effects.
    
    Args:
        ingredient: The food ingredient to search for (e.g., "BHA", "Sodium Nitrite")
        health_claim: The specific health concern (e.g., "carcinogenic effects", "toxicity")
        max_results: Maximum number of citations to return (1-10, default: 3)
        
    Returns:
        Formatted citations in APA style with DOI/PMID identifiers
    """
    try:
        # Validate input
        if not ingredient or not health_claim:
            return "Error: Both ingredient and health_claim are required"
        
        if max_results < 1 or max_results > 10:
            max_results = 3
        
        print(f"[MCP Citation Tool] Searching for: {ingredient} + {health_claim}")
        
        # Create search parameters
        search_params = CitationSearch(
            ingredient=ingredient,
            health_claim=health_claim,
            max_results=max_results,
            search_pubmed=True,
            search_crossref=True,
            search_web=False
        )
        
        # Perform search - note: this is a sync function but we're in async context
        # We'll need to handle this properly
        result = citation_service.search_citations(search_params)
        
        if not result.citations:
            return f"No citations found for '{ingredient}' and '{health_claim}'"
        
        # Format citations for return
        formatted_citations = []
        for i, citation in enumerate(result.citations, 1):
            formatted = f"{i}. {citation.to_apa_format()}"
            if citation.doi:
                formatted += f"\n   DOI: {citation.doi}"
            if citation.pmid:
                formatted += f"\n   PMID: {citation.pmid}"
            formatted_citations.append(formatted)
        
        response = f"Found {len(result.citations)} citations (search time: {result.search_time:.2f}s):\n\n"
        response += "\n\n".join(formatted_citations)
        
        if result.error:
            response += f"\n\nNote: Some search errors occurred: {result.error}"
        
        print(f"[MCP Citation Tool] Returning {len(result.citations)} citations")
        return response
        
    except Exception as e:
        error_msg = f"Citation search failed: {str(e)}"
        logger.error(error_msg)
        print(f"[MCP Citation Tool] Error: {error_msg}")
        return f"Error: {error_msg}"

@mcp_server.tool()
def verify_citation_exists(doi_or_pmid: str) -> str:
    """
    Verify that a specific citation actually exists by checking its DOI or PMID.
    
    Args:
        doi_or_pmid: Either a DOI (e.g., "10.1002/bmc.70103") or PMID (e.g., "12345678")
        
    Returns:
        Verification status and details
    """
    try:
        print(f"[MCP Citation Verify] Checking: {doi_or_pmid}")
        
        # Create a dummy citation to verify
        from app.models.citation import Citation, Author
        
        if doi_or_pmid.startswith("10."):
            # It's a DOI
            citation = Citation(
                title="Verification Check",
                authors=[Author(last_name="Unknown")],
                doi=doi_or_pmid,
                source_type="verification"
            )
        elif doi_or_pmid.isdigit():
            # It's a PMID
            citation = Citation(
                title="Verification Check", 
                authors=[Author(last_name="Unknown")],
                pmid=doi_or_pmid,
                source_type="verification"
            )
        else:
            return "Error: Please provide a valid DOI (starts with '10.') or PMID (numeric)"
        
        # Verify the citation
        exists = citation_service.verify_citation(citation)
        
        if exists:
            return f"✅ Citation verified: {doi_or_pmid} exists and is accessible"
        else:
            return f"❌ Citation not found: {doi_or_pmid} could not be verified"
            
    except Exception as e:
        error_msg = f"Citation verification failed: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"

def get_citation_server():
    """Get the FastMCP server instance for citation tools."""
    return mcp_server

# Test the MCP server
if __name__ == "__main__":
    print("Testing Citation MCP Server...")
    print("✅ MCP Server initialized successfully!")
    print(f"Server name: {mcp_server.name}")
    print("Server is ready to receive MCP client connections.")
    print("\nTo test the actual tools, connect an MCP client to this server.")
    print("The server exposes 2 tools:")
    print("1. search_health_citations - Search for scientific citations")
    print("2. verify_citation_exists - Verify DOI/PMID exists") 