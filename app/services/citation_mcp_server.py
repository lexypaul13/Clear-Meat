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
def fetch_article_abstract(doi_or_pmid: str) -> str:
    """
    Fetch the full abstract and details for a specific article by DOI or PMID.
    
    Args:
        doi_or_pmid: Either a DOI (e.g., "10.1002/bmc.70103") or PMID (e.g., "12345678")
        
    Returns:
        Full abstract and article details for analysis
    """
    try:
        print(f"[MCP Abstract Fetch] Fetching abstract for: {doi_or_pmid}")
        
        if doi_or_pmid.startswith("10."):
            # Fetch by DOI
            abstract_details = citation_service.fetch_abstract_by_doi(doi_or_pmid)
        elif doi_or_pmid.isdigit():
            # Fetch by PMID
            abstract_details = citation_service.fetch_abstract_by_pmid(doi_or_pmid)
        else:
            return "Error: Please provide a valid DOI (starts with '10.') or PMID (numeric)"
        
        if abstract_details:
            response = f"ARTICLE DETAILS:\n"
            response += f"Title: {abstract_details.get('title', 'Unknown')}\n"
            response += f"Authors: {abstract_details.get('authors', 'Unknown')}\n"
            response += f"Journal: {abstract_details.get('journal', 'Unknown')}\n"
            response += f"Year: {abstract_details.get('year', 'Unknown')}\n\n"
            response += f"ABSTRACT:\n{abstract_details.get('abstract', 'Abstract not available')}\n\n"
            response += f"DOI: {abstract_details.get('doi', 'N/A')}\n"
            response += f"PMID: {abstract_details.get('pmid', 'N/A')}"
            
            print(f"[MCP Abstract Fetch] Successfully fetched abstract ({len(abstract_details.get('abstract', ''))} chars)")
            return response
        else:
            return f"❌ Abstract not found for: {doi_or_pmid}"
            
    except Exception as e:
        error_msg = f"Abstract fetch failed: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"

@mcp_server.tool()
def search_and_extract_evidence(ingredient: str, health_claim: str, max_results: int = 2) -> str:
    """
    Search for scientific evidence and extract key health findings for an ingredient.
    
    Args:
        ingredient: The food ingredient to research (e.g., "BHA", "Sodium Nitrite")
        health_claim: The specific health concern (e.g., "carcinogenic effects", "toxicity")
        max_results: Maximum number of articles to analyze (1-5, default: 2)
        
    Returns:
        Structured evidence summary with key findings and citations
    """
    try:
        if not ingredient or not health_claim:
            return "Error: Both ingredient and health_claim are required"
        
        if max_results < 1 or max_results > 5:
            max_results = 2
        
        print(f"[MCP Evidence Extraction] Researching: {ingredient} + {health_claim}")
        
        # Step 1: Search for citations
        search_params = CitationSearch(
            ingredient=ingredient,
            health_claim=health_claim,
            max_results=max_results,
            search_pubmed=True,
            search_crossref=True,
            search_semantic_scholar=False,  # Focus on higher quality sources
            search_web=False
        )
        
        result = citation_service.search_citations(search_params)
        
        if not result.citations:
            return f"No scientific evidence found for '{ingredient}' and '{health_claim}'"
        
        # Step 2: Extract abstracts and key findings
        evidence_summary = f"SCIENTIFIC EVIDENCE FOR {ingredient.upper()}:\n"
        evidence_summary += f"Health Concern: {health_claim}\n"
        evidence_summary += f"Sources Analyzed: {len(result.citations)}\n\n"
        
        for i, citation in enumerate(result.citations, 1):
            evidence_summary += f"STUDY {i}:\n"
            evidence_summary += f"Title: {citation.title}\n"
            evidence_summary += f"Journal: {citation.journal or 'Unknown'}\n"
            evidence_summary += f"Year: {citation.publication_date.year if citation.publication_date else 'Unknown'}\n"
            
            if citation.abstract:
                # Extract key findings from abstract
                key_findings = citation_service.extract_key_findings(citation.abstract, ingredient, health_claim)
                evidence_summary += f"Key Findings: {key_findings}\n"
            else:
                evidence_summary += f"Abstract: Not available\n"
            
            evidence_summary += f"Citation: {citation.to_apa_format()}\n"
            if citation.doi:
                evidence_summary += f"DOI: {citation.doi}\n"
            if citation.pmid:
                evidence_summary += f"PMID: {citation.pmid}\n"
            evidence_summary += "\n"
        
        print(f"[MCP Evidence Extraction] Extracted evidence from {len(result.citations)} studies")
        return evidence_summary
        
    except Exception as e:
        error_msg = f"Evidence extraction failed: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"

@mcp_server.tool()
def summarize_health_evidence(evidence_text: str, ingredient: str, max_chars: int = 180) -> str:
    """
    Generate a concise, plain English health summary from scientific evidence.
    
    Args:
        evidence_text: The scientific evidence text to summarize
        ingredient: The ingredient being analyzed
        max_chars: Maximum characters for the summary (default: 180)
        
    Returns:
        Concise health summary suitable for micro-reports
    """
    try:
        print(f"[MCP Evidence Summary] Summarizing evidence for: {ingredient}")
        
        if not evidence_text or not ingredient:
            return "Error: Both evidence_text and ingredient are required"
        
        if max_chars < 50 or max_chars > 300:
            max_chars = 180
        
        # Use the citation service to generate a concise summary
        summary = citation_service.generate_health_summary(evidence_text, ingredient, max_chars)
        
        if summary:
            print(f"[MCP Evidence Summary] Generated summary ({len(summary)} chars)")
            return summary
        else:
            return f"Unable to generate summary for {ingredient}"
            
    except Exception as e:
        error_msg = f"Evidence summarization failed: {str(e)}"
        logger.error(error_msg)
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