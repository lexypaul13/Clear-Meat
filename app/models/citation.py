"""Citation models for scientific literature references."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class Author(BaseModel):
    """Author information for citations."""
    first_name: Optional[str] = None
    last_name: str
    affiliation: Optional[str] = None


class Citation(BaseModel):
    """Scientific citation model."""
    citation_id: Optional[str] = Field(default=None, description="Unique identifier (DOI, PMID, or generated)")
    title: str
    authors: List[Author]
    journal: Optional[str] = None
    publication_date: Optional[datetime] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    source_type: str = Field(..., description="pubmed, crossref, web")
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    
    @field_validator('citation_id')
    @classmethod
    def generate_citation_id(cls, v, info):
        """Generate citation ID if not provided."""
        if v:
            return v
        
        # Get other field values
        values = info.data if hasattr(info, 'data') else {}
        
        # Use DOI or PMID as ID if available
        if 'doi' in values and values['doi']:
            return values['doi']
        if 'pmid' in values and values['pmid']:
            return f"PMID:{values['pmid']}"
        
        # Generate from title and first author
        if 'title' in values and 'authors' in values and values['authors']:
            first_author = values['authors'][0].last_name
            title_words = values['title'].split()[:3]
            return f"{first_author}_{'-'.join(title_words)}"
        
        return f"citation_{datetime.now().timestamp()}"

    def to_apa_format(self) -> str:
        """Format citation in APA style."""
        # Build author list
        if not self.authors:
            author_str = "Unknown Author"
        elif len(self.authors) == 1:
            author_str = f"{self.authors[0].last_name}, {self.authors[0].first_name[0] if self.authors[0].first_name else ''}.".strip()
        else:
            authors_list = []
            for i, author in enumerate(self.authors[:6]):  # APA limits to 6 authors
                if i < len(self.authors) - 1:
                    authors_list.append(f"{author.last_name}, {author.first_name[0] if author.first_name else ''}.")
                else:
                    authors_list.append(f"& {author.last_name}, {author.first_name[0] if author.first_name else ''}.")
            if len(self.authors) > 6:
                authors_list.append("et al.")
            author_str = " ".join(authors_list)
        
        # Build year
        year = f"({self.publication_date.year})" if self.publication_date else "(n.d.)"
        
        # Build title
        title = self.title.rstrip('.')
        
        # Build journal info
        journal_info = ""
        if self.journal:
            journal_info = f" {self.journal}"
            if self.volume:
                journal_info += f", {self.volume}"
                if self.issue:
                    journal_info += f"({self.issue})"
            if self.pages:
                journal_info += f", {self.pages}"
        
        # Build DOI/URL
        identifier = ""
        if self.doi:
            identifier = f" https://doi.org/{self.doi}"
        elif self.pmid:
            identifier = f" PMID: {self.pmid}"
        elif self.url:
            identifier = f" {self.url}"
        
        return f"{author_str} {year}. {title}.{journal_info}.{identifier}".replace("..", ".")


class CitationSearch(BaseModel):
    """Search parameters for finding citations."""
    ingredient: str
    health_claim: str
    max_results: int = Field(default=5, ge=1, le=20)
    
    # Academic sources
    search_pubmed: bool = True
    search_crossref: bool = True
    
    # Official sources
    search_fda: bool = True
    search_who: bool = True
    search_harvard_health: bool = True
    search_cdc: bool = True
    search_mayo_clinic: bool = True
    search_nih: bool = True
    
    # Free research databases
    search_doaj: bool = True  # Directory of Open Access Journals
    search_arxiv: bool = True  # arXiv preprint server
    search_biorxiv: bool = True  # Biology preprint server
    search_europe_pmc: bool = True  # European biomedical literature
    
    search_web: bool = False  # Keep general web search disabled for now
    
    year_range: Optional[tuple[int, int]] = None


class CitationResult(BaseModel):
    """Result of citation search."""
    search_params: CitationSearch
    citations: List[Citation]
    total_found: int
    search_time: float
    error: Optional[str] = None

    def get_formatted_citations(self) -> Dict[str, str]:
        """Get citations formatted for inclusion in health assessment."""
        formatted = {}
        for i, citation in enumerate(self.citations, 1):
            formatted[str(i)] = citation.to_apa_format()
        return formatted


 