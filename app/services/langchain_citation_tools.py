"""LangChain tools for citation search integration with Gemini."""
import json
from typing import List, Dict, Any
from langchain.tools import tool
from langchain.pydantic_v1 import BaseModel, Field

from app.services.citation_tools import CitationSearchService
from app.models.citation import CitationSearch

# Initialize citation service
citation_service = CitationSearchService()


class CitationSearchInput(BaseModel):
    """Input for citation search."""
    ingredient: str = Field(description="The food ingredient to search for (e.g., 'Salt', 'Sugar', 'Sodium Nitrite')")
    health_claim: str = Field(description="The health concern to search for (e.g., 'health effects', 'toxicity', 'cancer risk')")
    max_results: int = Field(default=2, description="Maximum number of citations to return (1-5)")


@tool("search_fda_citations", args_schema=CitationSearchInput)
def search_fda_citations(ingredient: str, health_claim: str, max_results: int = 2) -> str:
    """Search FDA.gov for official guidance and reports about food ingredient health effects.
    
    Returns real FDA articles with titles and clickable URLs.
    """
    try:
        search_params = CitationSearch(
            ingredient=ingredient,
            health_claim=health_claim,
            max_results=max_results,
            search_fda=True,
            search_cdc=False,
            search_mayo_clinic=False,
            search_pubmed=False
        )
        
        result = citation_service.search_citations(search_params)
        
        if not result.citations:
            return f"No FDA citations found for '{ingredient}' and '{health_claim}'"
        
        # Format citations for LangChain response
        citations_list = []
        for citation in result.citations:
            citations_list.append({
                "title": citation.title,
                "url": citation.url,
                "source": "FDA.gov",
                "abstract": citation.abstract[:150] + "..." if len(citation.abstract) > 150 else citation.abstract
            })
        
        return json.dumps({
            "source": "FDA",
            "citations": citations_list
        })
        
    except Exception as e:
        return f"Error searching FDA: {str(e)}"


@tool("search_cdc_citations", args_schema=CitationSearchInput)
def search_cdc_citations(ingredient: str, health_claim: str, max_results: int = 2) -> str:
    """Search CDC.gov for health guidance about food ingredients and their health impacts.
    
    Returns real CDC articles with titles and clickable URLs.
    """
    try:
        search_params = CitationSearch(
            ingredient=ingredient,
            health_claim=health_claim,
            max_results=max_results,
            search_fda=False,
            search_cdc=True,
            search_mayo_clinic=False,
            search_pubmed=False
        )
        
        result = citation_service.search_citations(search_params)
        
        if not result.citations:
            return f"No CDC citations found for '{ingredient}' and '{health_claim}'"
        
        # Format citations for LangChain response
        citations_list = []
        for citation in result.citations:
            citations_list.append({
                "title": citation.title,
                "url": citation.url,
                "source": "CDC.gov",
                "abstract": citation.abstract[:150] + "..." if len(citation.abstract) > 150 else citation.abstract
            })
        
        return json.dumps({
            "source": "CDC",
            "citations": citations_list
        })
        
    except Exception as e:
        return f"Error searching CDC: {str(e)}"


@tool("search_mayo_clinic_citations", args_schema=CitationSearchInput)
def search_mayo_clinic_citations(ingredient: str, health_claim: str, max_results: int = 2) -> str:
    """Search Mayo Clinic for medical guidance about food ingredients and health effects.
    
    Returns real Mayo Clinic articles with titles and clickable URLs.
    """
    try:
        search_params = CitationSearch(
            ingredient=ingredient,
            health_claim=health_claim,
            max_results=max_results,
            search_fda=False,
            search_cdc=False,
            search_mayo_clinic=True,
            search_pubmed=False
        )
        
        result = citation_service.search_citations(search_params)
        
        if not result.citations:
            return f"No Mayo Clinic citations found for '{ingredient}' and '{health_claim}'"
        
        # Format citations for LangChain response
        citations_list = []
        for citation in result.citations:
            citations_list.append({
                "title": citation.title,
                "url": citation.url,
                "source": "Mayo Clinic",
                "abstract": citation.abstract[:150] + "..." if len(citation.abstract) > 150 else citation.abstract
            })
        
        return json.dumps({
            "source": "Mayo Clinic",
            "citations": citations_list
        })
        
    except Exception as e:
        return f"Error searching Mayo Clinic: {str(e)}"


@tool("search_all_health_citations", args_schema=CitationSearchInput)
def search_all_health_citations(ingredient: str, health_claim: str, max_results: int = 3) -> str:
    """Search FDA, CDC, and Mayo Clinic for comprehensive health guidance about food ingredients.
    
    Returns real articles from multiple authoritative sources with titles and clickable URLs.
    """
    try:
        search_params = CitationSearch(
            ingredient=ingredient,
            health_claim=health_claim,
            max_results=max_results,
            search_fda=True,
            search_cdc=True,
            search_mayo_clinic=True,
            search_pubmed=False
        )
        
        result = citation_service.search_citations(search_params)
        
        if not result.citations:
            return f"No citations found for '{ingredient}' and '{health_claim}'"
        
        # Format citations for LangChain response
        citations_list = []
        for citation in result.citations:
            source = "Research"
            if citation.source_type == "fda_web":
                source = "FDA"
            elif citation.source_type == "cdc_web":
                source = "CDC"
            elif citation.source_type == "mayo_clinic_web":
                source = "Mayo Clinic"
                
            citations_list.append({
                "title": citation.title,
                "url": citation.url,
                "source": source,
                "year": citation.publication_date.year if citation.publication_date else 2024,
                "abstract": citation.abstract[:150] + "..." if len(citation.abstract) > 150 else citation.abstract
            })
        
        return json.dumps({
            "source": "Multiple Health Authorities",
            "citations": citations_list
        })
        
    except Exception as e:
        return f"Error searching health citations: {str(e)}"


# Export all tools
citation_tools = [
    search_fda_citations,
    search_cdc_citations,
    search_mayo_clinic_citations,
    search_all_health_citations
]