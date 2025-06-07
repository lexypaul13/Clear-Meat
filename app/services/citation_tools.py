"""Citation search tools for finding real scientific literature."""
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests
from pymed import PubMed

from app.models.citation import Citation, Author, CitationSearch, CitationResult

logger = logging.getLogger(__name__)


class CitationSearchService:
    """Service for searching scientific citations from multiple sources."""
    
    def __init__(self):
        self.pubmed = PubMed(tool="Clear-Meat", email="api@clear-meat.com")
        
    def search_citations(self, search_params: CitationSearch) -> CitationResult:
        """
        Search for citations from multiple sources based on search parameters.
        
        Args:
            search_params: CitationSearch object with ingredient and health claim
            
        Returns:
            CitationResult with found citations
        """
        start_time = time.time()
        all_citations = []
        errors = []
        
        # Build search query
        query = f"{search_params.ingredient} {search_params.health_claim}"
        print(f"[Citation Search] Searching for: {query}")
        
        # Search PubMed
        if search_params.search_pubmed:
            try:
                pubmed_citations = self._search_pubmed(query, search_params.max_results)
                all_citations.extend(pubmed_citations)
                print(f"[PubMed] Found {len(pubmed_citations)} citations")
            except Exception as e:
                error_msg = f"PubMed search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                print(f"[PubMed] Error: {error_msg}")
        
        # Search CrossRef
        if search_params.search_crossref:
            try:
                crossref_citations = self._search_crossref(query, search_params.max_results)
                all_citations.extend(crossref_citations)
                print(f"[CrossRef] Found {len(crossref_citations)} citations")
            except Exception as e:
                error_msg = f"CrossRef search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                print(f"[CrossRef] Error: {error_msg}")
        
        # Remove duplicates based on title similarity
        unique_citations = self._deduplicate_citations(all_citations)
        
        # Sort by relevance score if available
        unique_citations.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        
        # Limit to max results
        final_citations = unique_citations[:search_params.max_results]
        
        search_time = time.time() - start_time
        
        result = CitationResult(
            search_params=search_params,
            citations=final_citations,
            total_found=len(unique_citations),
            search_time=search_time,
            error="; ".join(errors) if errors else None
        )
        
        print(f"[Citation Search] Completed in {search_time:.2f}s. Found {len(final_citations)} unique citations")
        return result
    
    def _search_pubmed(self, query: str, max_results: int) -> List[Citation]:
        """Search PubMed for relevant citations."""
        citations = []
        
        try:
            # Search PubMed
            results = list(self.pubmed.query(query, max_results=max_results * 2))  # Get more to filter
            
            for article in results:
                try:
                    # Parse authors
                    authors = []
                    if hasattr(article, 'authors') and article.authors:
                        for author in article.authors[:10]:  # Limit authors
                            # Handle different author formats
                            if isinstance(author, dict):
                                first_name = author.get('firstname', '')
                                last_name = author.get('lastname', '')
                            else:
                                # Try to parse string format
                                parts = str(author).split(' ')
                                last_name = parts[-1] if parts else ''
                                first_name = ' '.join(parts[:-1]) if len(parts) > 1 else ''
                            
                            if last_name:
                                authors.append(Author(
                                    first_name=first_name,
                                    last_name=last_name
                                ))
                    
                    # Parse publication date
                    pub_date = None
                    if hasattr(article, 'publication_date') and article.publication_date:
                        try:
                            if isinstance(article.publication_date, str):
                                pub_date = datetime.strptime(article.publication_date, "%Y-%m-%d")
                            else:
                                pub_date = article.publication_date
                        except:
                            pass
                    
                    # Create citation
                    citation = Citation(
                        title=article.title or "Unknown Title",
                        authors=authors or [Author(last_name="Unknown")],
                        journal=getattr(article, 'journal', None),
                        publication_date=pub_date,
                        volume=getattr(article, 'volume', None),
                        issue=getattr(article, 'issue', None),
                        pages=getattr(article, 'pages', None),
                        doi=getattr(article, 'doi', None),
                        pmid=str(article.pubmed_id) if hasattr(article, 'pubmed_id') else None,
                        abstract=getattr(article, 'abstract', None),
                        source_type="pubmed",
                        relevance_score=0.9  # PubMed results are generally highly relevant
                    )
                    
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing PubMed article: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            raise
        
        return citations
    
    def _search_crossref(self, query: str, max_results: int) -> List[Citation]:
        """Search CrossRef for relevant citations."""
        citations = []
        
        try:
            # Search CrossRef using their REST API directly
            print(f"[CrossRef] Searching for: {query}")
            
            # CrossRef API endpoint
            url = "https://api.crossref.org/works"
            params = {
                'query': query,
                'rows': max_results * 2,  # Get more to filter
                'select': 'DOI,title,author,container-title,published-print,published-online,volume,issue,page,URL,abstract',
                'sort': 'relevance'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('message', {}).get('items', [])
            
            for item in items:
                try:
                    # Parse authors
                    authors = []
                    if 'author' in item:
                        for author in item['author'][:10]:  # Limit authors
                            authors.append(Author(
                                first_name=author.get('given', ''),
                                last_name=author.get('family', 'Unknown')
                            ))
                    
                    # Parse publication date
                    pub_date = None
                    if 'published-print' in item:
                        date_parts = item['published-print'].get('date-parts', [[]])[0]
                        if len(date_parts) >= 1:
                            year = date_parts[0]
                            month = date_parts[1] if len(date_parts) > 1 else 1
                            day = date_parts[2] if len(date_parts) > 2 else 1
                            pub_date = datetime(year, month, day)
                    elif 'published-online' in item:
                        date_parts = item['published-online'].get('date-parts', [[]])[0]
                        if len(date_parts) >= 1:
                            year = date_parts[0]
                            month = date_parts[1] if len(date_parts) > 1 else 1
                            day = date_parts[2] if len(date_parts) > 2 else 1
                            pub_date = datetime(year, month, day)
                    
                    # Get title
                    title = item.get('title', ['Unknown Title'])
                    if isinstance(title, list) and title:
                        title = title[0]
                    
                    # Create citation
                    citation = Citation(
                        title=title,
                        authors=authors or [Author(last_name="Unknown")],
                        journal=' '.join(item.get('container-title', [])),
                        publication_date=pub_date,
                        volume=item.get('volume'),
                        issue=item.get('issue'),
                        pages=item.get('page'),
                        doi=item.get('DOI'),
                        url=item.get('URL'),
                        abstract=item.get('abstract'),
                        source_type="crossref",
                        relevance_score=0.7  # CrossRef results are generally relevant
                    )
                    
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing CrossRef item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"CrossRef search error: {e}")
            raise
        
        return citations
    
    def _deduplicate_citations(self, citations: List[Citation]) -> List[Citation]:
        """Remove duplicate citations based on title similarity."""
        unique_citations = []
        seen_titles = set()
        
        for citation in citations:
            # Normalize title for comparison
            normalized_title = citation.title.lower().strip()
            normalized_title = ''.join(c for c in normalized_title if c.isalnum() or c.isspace())
            
            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_citations.append(citation)
        
        return unique_citations
    
    def verify_citation(self, citation: Citation) -> bool:
        """
        Verify that a citation actually exists.
        
        Args:
            citation: Citation to verify
            
        Returns:
            True if citation is verified to exist
        """
        # Check DOI if available
        if citation.doi:
            try:
                response = requests.get(f"https://doi.org/{citation.doi}", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
        
        # Check PMID if available
        if citation.pmid:
            try:
                results = list(self.pubmed.query(f"PMID:{citation.pmid}", max_results=1))
                if results:
                    return True
            except:
                pass
        
        return False


# Test the citation search
if __name__ == "__main__":
    # Initialize service
    service = CitationSearchService()
    
    # Test search
    search_params = CitationSearch(
        ingredient="BHA",
        health_claim="carcinogenic effects",
        max_results=3
    )
    
    print("Testing citation search...")
    result = service.search_citations(search_params)
    
    print(f"\nFound {len(result.citations)} citations:")
    for i, citation in enumerate(result.citations, 1):
        print(f"\n{i}. {citation.to_apa_format()}")
        if citation.doi:
            print(f"   DOI: {citation.doi}")
        if citation.pmid:
            print(f"   PMID: {citation.pmid}") 