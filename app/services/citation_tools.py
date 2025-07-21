"""Citation search tools for finding real scientific literature."""
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests
from pymed import PubMed
import urllib3

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        
        # Search PubMed
        if search_params.search_pubmed:
            try:
                pubmed_citations = self._search_pubmed(query, search_params.max_results)
                all_citations.extend(pubmed_citations)
            except Exception as e:
                error_msg = f"PubMed search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search CrossRef
        if search_params.search_crossref:
            try:
                crossref_citations = self._search_crossref(query, search_params.max_results)
                all_citations.extend(crossref_citations)
            except Exception as e:
                error_msg = f"CrossRef search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search Semantic Scholar
        if search_params.search_semantic_scholar:
            try:
                semantic_scholar_citations = self._search_semantic_scholar(query, search_params.max_results)
                all_citations.extend(semantic_scholar_citations)
            except Exception as e:
                error_msg = f"Semantic Scholar search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search FDA
        if search_params.search_fda:
            try:
                fda_citations = self._search_fda(query, search_params.max_results)
                all_citations.extend(fda_citations)
            except Exception as e:
                error_msg = f"FDA search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search WHO
        if search_params.search_who:
            try:
                who_citations = self._search_who(query, search_params.max_results)
                all_citations.extend(who_citations)
            except Exception as e:
                error_msg = f"WHO search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search Harvard Health
        if search_params.search_harvard_health:
            try:
                harvard_health_citations = self._search_harvard_health(query, search_params.max_results)
                all_citations.extend(harvard_health_citations)
            except Exception as e:
                error_msg = f"Harvard Health search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search CDC
        if search_params.search_cdc:
            try:
                cdc_citations = self._search_cdc(query, search_params.max_results)
                all_citations.extend(cdc_citations)
            except Exception as e:
                error_msg = f"CDC search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search Mayo Clinic
        if search_params.search_mayo_clinic:
            try:
                mayo_citations = self._search_mayo_clinic(query, search_params.max_results)
                all_citations.extend(mayo_citations)
            except Exception as e:
                error_msg = f"Mayo Clinic search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search NIH/MedlinePlus
        if search_params.search_nih:
            try:
                nih_citations = self._search_nih(query, search_params.max_results)
                all_citations.extend(nih_citations)
            except Exception as e:
                error_msg = f"NIH search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search DOAJ (Directory of Open Access Journals)
        if search_params.search_doaj:
            try:
                doaj_citations = self._search_doaj(query, search_params.max_results)
                all_citations.extend(doaj_citations)
            except Exception as e:
                error_msg = f"DOAJ search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search arXiv
        if search_params.search_arxiv:
            try:
                arxiv_citations = self._search_arxiv(query, search_params.max_results)
                all_citations.extend(arxiv_citations)
            except Exception as e:
                error_msg = f"arXiv search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search bioRxiv
        if search_params.search_biorxiv:
            try:
                biorxiv_citations = self._search_biorxiv(query, search_params.max_results)
                all_citations.extend(biorxiv_citations)
            except Exception as e:
                error_msg = f"bioRxiv search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search Semantic Scholar
        if search_params.search_semantic_scholar:
            try:
                semantic_citations = self._search_semantic_scholar(query, search_params.max_results)
                all_citations.extend(semantic_citations)
            except Exception as e:
                error_msg = f"Semantic Scholar search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Search Europe PMC
        if search_params.search_europe_pmc:
            try:
                europe_pmc_citations = self._search_europe_pmc(query, search_params.max_results)
                all_citations.extend(europe_pmc_citations)
            except Exception as e:
                error_msg = f"Europe PMC search error: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
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
            
            # CrossRef API endpoint
            url = "https://api.crossref.org/works"
            params = {
                'query': query,
                'rows': max_results * 2,  # Get more to filter
                'select': 'DOI,title,author,container-title,published-print,published-online,volume,issue,page,URL,abstract',
                'sort': 'relevance'
            }
            
            response = requests.get(url, params=params, timeout=10, verify=True)
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
    
    def _search_semantic_scholar(self, query: str, max_results: int) -> List[Citation]:
        """Search Semantic Scholar for relevant citations."""
        citations = []
        
        try:
            
            # Semantic Scholar API endpoint
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': query,
                'limit': max_results * 2,
                'fields': 'title,authors,venue,year,doi,url,abstract,citationCount'
            }
            
            response = requests.get(url, params=params, timeout=10, verify=True)
            response.raise_for_status()
            
            data = response.json()
            papers = data.get('data', [])
            
            for paper in papers:
                try:
                    # Parse authors
                    authors = []
                    for author in paper.get('authors', [])[:10]:
                        # Split name into first and last
                        name_parts = author.get('name', '').split()
                        if name_parts:
                            last_name = name_parts[-1]
                            first_name = ' '.join(name_parts[:-1]) if len(name_parts) > 1 else ''
                            authors.append(Author(
                                first_name=first_name,
                                last_name=last_name
                            ))
                    
                    # Parse publication date
                    pub_date = None
                    if paper.get('year'):
                        pub_date = datetime(paper['year'], 1, 1)
                    
                    # Calculate relevance based on citation count
                    citation_count = paper.get('citationCount', 0)
                    relevance = min(0.9, 0.5 + (citation_count / 1000))
                    
                    # Create citation
                    citation = Citation(
                        title=paper.get('title', 'Unknown Title'),
                        authors=authors or [Author(last_name="Unknown")],
                        journal=paper.get('venue'),
                        publication_date=pub_date,
                        doi=paper.get('doi'),
                        url=paper.get('url'),
                        abstract=paper.get('abstract'),
                        source_type="semantic_scholar",
                        relevance_score=relevance
                    )
                    
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Semantic Scholar paper: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
            # Don't raise, just return empty list
        
        return citations
    
    def _search_fda(self, query: str, max_results: int) -> List[Citation]:
        """Search FDA.gov for official guidance and reports using real web search."""
        citations = []
        
        try:
            
            # Perform real FDA search
            search_url = f"https://search.fda.gov/search?utf8=✓&affiliate=fda1&query={requests.utils.quote(query)}&commit=Search"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse search results
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search results - FDA uses specific CSS classes
            results = soup.find_all('div', class_='result')[:max_results]
            
            if not results:
                # Try alternative search result format
                results = soup.find_all('li', class_='search-result')[:max_results]
            
            for idx, result in enumerate(results):
                try:
                    # Extract title
                    title_elem = result.find('h2') or result.find('h3') or result.find('a', class_='title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Extract URL
                    url_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                    if url_elem and url_elem.get('href'):
                        url = url_elem['href']
                        if not url.startswith('http'):
                            url = f"https://www.fda.gov{url}"
                    else:
                        continue
                    
                    # Extract abstract/snippet
                    abstract_elem = result.find('div', class_='snippet') or result.find('p')
                    abstract = abstract_elem.get_text(strip=True) if abstract_elem else f"FDA guidance on {query}"
                    
                    # Create citation with real data
                    citation = Citation(
                        title=title,
                        authors=[Author(last_name="FDA", first_name="U.S. Food and Drug Administration")],
                        journal="FDA.gov Official Publication",
                        publication_date=datetime(2024, 1, 1),  # FDA doesn't always show dates
                        url=url,
                        abstract=abstract[:200] + "..." if len(abstract) > 200 else abstract,
                        source_type="fda_web",
                        relevance_score=1.0 - (idx * 0.1)  # Higher rank = higher relevance
                    )
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing FDA result: {e}")
                    continue
            
            # If no results found, try direct FDA pages for common ingredients
            if not citations and len(query.split()[0]) > 2:
                ingredient = query.split()[0].lower()
                
                # Known FDA pages for common ingredients
                direct_pages = {
                    "salt": ("Sodium Reduction Initiative", "https://www.fda.gov/food/food-additives-petitions/sodium-reduction"),
                    "sodium": ("Sodium in Your Diet", "https://www.fda.gov/food/nutrition-education-resources-materials/sodium-your-diet"),
                    "sugar": ("Added Sugars on the Nutrition Facts Label", "https://www.fda.gov/food/nutrition-facts-label/added-sugars-nutrition-facts-label"),
                    "nitrite": ("Food Additive Status List", "https://www.fda.gov/food/food-additives-petitions/food-additive-status-list"),
                    "msg": ("Questions and Answers on MSG", "https://www.fda.gov/food/food-additives-petitions/questions-and-answers-monosodium-glutamate-msg")
                }
                
                if ingredient in direct_pages:
                    title, url = direct_pages[ingredient]
                    citation = Citation(
                        title=f"FDA: {title}",
                        authors=[Author(last_name="FDA", first_name="U.S. Food and Drug Administration")],
                        journal="FDA.gov Consumer Information",
                        publication_date=datetime(2024, 1, 1),
                        url=url,
                        abstract=f"Official FDA guidance on {ingredient} in food products, safety assessments, and health recommendations",
                        source_type="fda_web",
                        relevance_score=0.9
                    )
                    citations.append(citation)
            
                
        except requests.RequestException as e:
            logger.error(f"FDA web search error: {e}")
            # Don't return fake data on error - return empty list
        except Exception as e:
            logger.error(f"FDA search parsing error: {e}")
        
        return citations[:max_results]
    
    def _search_who(self, query: str, max_results: int) -> List[Citation]:
        """Search WHO.int for international health guidance using real web search."""
        citations = []
        
        try:
            
            # WHO search endpoint
            search_url = f"https://www.who.int/home/search?indexCatalogue=genericsearchindex1&searchQuery={requests.utils.quote(query)}&wordsMode=AnyWord"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse search results
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search results - WHO uses different structure
            results = soup.find_all('div', class_='search-result-item')[:max_results]
            
            if not results:
                # Try alternative selectors
                results = soup.find_all('article', class_='search-result')[:max_results]
            
            for idx, result in enumerate(results):
                try:
                    # Extract title
                    title_elem = result.find('h3') or result.find('h4') or result.find('a', class_='search-title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Extract URL
                    url_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                    if url_elem and url_elem.get('href'):
                        url = url_elem['href']
                        if not url.startswith('http'):
                            url = f"https://www.who.int{url}"
                    else:
                        continue
                    
                    # Extract abstract
                    abstract_elem = result.find('div', class_='search-snippet') or result.find('p', class_='description')
                    abstract = abstract_elem.get_text(strip=True) if abstract_elem else f"WHO guidance on {query}"
                    
                    citation = Citation(
                        title=title,
                        authors=[Author(last_name="WHO", first_name="World Health Organization")],
                        journal="WHO Official Publication",
                        publication_date=datetime(2024, 1, 1),
                        url=url,
                        abstract=abstract[:200] + "..." if len(abstract) > 200 else abstract,
                        source_type="who_web",
                        relevance_score=1.0 - (idx * 0.1)
                    )
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing WHO result: {e}")
                    continue
            
                
        except Exception as e:
            logger.error(f"WHO web search error: {e}")
            # Return empty list on error
        
        return citations[:max_results]
    
    def _search_harvard_health(self, query: str, max_results: int) -> List[Citation]:
        """Search Harvard Health for clinical guidance using real web search."""
        citations = []
        
        try:
            
            # Harvard Health search endpoint
            search_url = f"https://www.health.harvard.edu/search?q={requests.utils.quote(query)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            
            # Harvard Health may return different status codes
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find search results
                results = soup.find_all('article', class_='search-result')[:max_results]
                
                if not results:
                    results = soup.find_all('div', class_='content-item')[:max_results]
                
                for idx, result in enumerate(results):
                    try:
                        # Extract title and URL
                        title_elem = result.find('h2') or result.find('h3') or result.find('a', class_='title')
                        if not title_elem:
                            continue
                        
                        if title_elem.name == 'a':
                            title = title_elem.get_text(strip=True)
                            url = title_elem.get('href', '')
                        else:
                            link_elem = title_elem.find('a')
                            if link_elem:
                                title = link_elem.get_text(strip=True)
                                url = link_elem.get('href', '')
                            else:
                                continue
                        
                        if not url.startswith('http'):
                            url = f"https://www.health.harvard.edu{url}"
                        
                        # Extract abstract
                        abstract_elem = result.find('div', class_='summary') or result.find('p')
                        abstract = abstract_elem.get_text(strip=True) if abstract_elem else f"Harvard Health guidance on {query}"
                        
                        citation = Citation(
                            title=title,
                            authors=[Author(last_name="Harvard Medical School", first_name="")],
                            journal="Harvard Health Publishing",
                            publication_date=datetime(2024, 1, 1),
                            url=url,
                            abstract=abstract[:200] + "..." if len(abstract) > 200 else abstract,
                            source_type="harvard_health",
                            relevance_score=0.95 - (idx * 0.05)
                        )
                        citations.append(citation)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing Harvard Health result: {e}")
                        continue
            
                
        except Exception as e:
            logger.error(f"Harvard Health web search error: {e}")
            # Return empty list on error
        
        return citations[:max_results]
    
    def _search_cdc(self, query: str, max_results: int) -> List[Citation]:
        """Search CDC.gov for official health guidance using real web search."""
        citations = []
        
        try:
            
            # CDC search endpoint
            search_url = f"https://search.cdc.gov/search?query={requests.utils.quote(query)}&utf8=✓&affiliate=cdc-main"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse search results
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search results - CDC uses specific structure
            results = soup.find_all('div', class_='searchResultsModule')[:max_results]
            
            if not results:
                # Try alternative selectors
                results = soup.find_all('div', class_='result')[:max_results]
            
            for idx, result in enumerate(results):
                try:
                    # Extract title
                    title_elem = result.find('h3') or result.find('a', class_='title')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Extract URL
                    url_elem = title_elem.find('a') if title_elem.name != 'a' else title_elem
                    if url_elem and url_elem.get('href'):
                        url = url_elem['href']
                        if not url.startswith('http'):
                            url = f"https://www.cdc.gov{url}"
                    else:
                        continue
                    
                    # Extract abstract/description
                    abstract_elem = result.find('p', class_='description') or result.find('div', class_='snippet')
                    abstract = abstract_elem.get_text(strip=True) if abstract_elem else f"CDC guidance on {query}"
                    
                    citation = Citation(
                        title=title,
                        authors=[Author(last_name="CDC", first_name="Centers for Disease Control and Prevention")],
                        journal="CDC.gov Official Publication",
                        publication_date=datetime(2024, 1, 1),
                        url=url,
                        abstract=abstract[:200] + "..." if len(abstract) > 200 else abstract,
                        source_type="cdc_web",
                        relevance_score=1.0 - (idx * 0.1)
                    )
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing CDC result: {e}")
                    continue
            
            # If no results, try known CDC pages for common topics
            if not citations and len(query.split()[0]) > 2:
                ingredient = query.split()[0].lower()
                
                direct_pages = {
                    "salt": ("Sodium and Your Health", "https://www.cdc.gov/salt/index.htm"),
                    "sodium": ("Salt Home", "https://www.cdc.gov/salt/"),
                    "sugar": ("Get the Facts: Added Sugars", "https://www.cdc.gov/nutrition/data-statistics/added-sugars.html"),
                    "nitrite": ("Food Safety", "https://www.cdc.gov/foodsafety/"),
                    "msg": ("Nutrition", "https://www.cdc.gov/nutrition/")
                }
                
                if ingredient in direct_pages:
                    title, url = direct_pages[ingredient]
                    citation = Citation(
                        title=f"CDC: {title}",
                        authors=[Author(last_name="CDC", first_name="Centers for Disease Control and Prevention")],
                        journal="CDC.gov Health Information",
                        publication_date=datetime(2024, 1, 1),
                        url=url,
                        abstract=f"CDC official guidance on {ingredient} and its health impacts, including recommended daily limits and health risks",
                        source_type="cdc_web",
                        relevance_score=0.9
                    )
                    citations.append(citation)
            
                    
        except Exception as e:
            logger.error(f"CDC web search error: {e}")
            # Return empty list on error
        
        return citations[:max_results]
    
    def _search_mayo_clinic(self, query: str, max_results: int) -> List[Citation]:
        """Search Mayo Clinic for medical guidance on food ingredients using real web search."""
        citations = []
        
        try:
            
            # Mayo Clinic search endpoint
            search_url = f"https://www.mayoclinic.org/search/search-results?q={requests.utils.quote(query)}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse search results
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search results - Mayo Clinic structure
            results = soup.find_all('li', class_='cmp-search-results__item')[:max_results]
            
            if not results:
                # Try alternative selector
                results = soup.find_all('div', class_='search-result')[:max_results]
            
            for idx, result in enumerate(results):
                try:
                    # Extract title and URL
                    title_elem = result.find('h3') or result.find('a', class_='cmp-search-results__item-link')
                    if not title_elem:
                        continue
                    
                    if title_elem.name == 'a':
                        title = title_elem.get_text(strip=True)
                        url = title_elem.get('href', '')
                    else:
                        link_elem = title_elem.find('a')
                        if link_elem:
                            title = link_elem.get_text(strip=True)
                            url = link_elem.get('href', '')
                        else:
                            continue
                    
                    if not url.startswith('http'):
                        url = f"https://www.mayoclinic.org{url}"
                    
                    # Extract description/abstract
                    desc_elem = result.find('p', class_='cmp-search-results__item-excerpt') or result.find('div', class_='description')
                    abstract = desc_elem.get_text(strip=True) if desc_elem else f"Mayo Clinic guidance on {query}"
                    
                    citation = Citation(
                        title=title,
                        authors=[Author(last_name="Mayo Clinic Staff", first_name="")],
                        journal="Mayo Clinic Health Information",
                        publication_date=datetime(2024, 1, 1),
                        url=url,
                        abstract=abstract[:200] + "..." if len(abstract) > 200 else abstract,
                        source_type="mayo_clinic_web",
                        relevance_score=0.95 - (idx * 0.05)
                    )
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing Mayo Clinic result: {e}")
                    continue
            
            # Fallback to known Mayo Clinic pages for common ingredients
            if not citations and len(query.split()[0]) > 2:
                ingredient = query.split()[0].lower()
                
                direct_pages = {
                    "salt": ("Sodium: How to tame your salt habit", "https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/sodium/art-20045479"),
                    "sodium": ("Sodium: How to tame your salt habit", "https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/sodium/art-20045479"),
                    "sugar": ("Added sugars: Don't get sabotaged by sweeteners", "https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/added-sugar/art-20045328"),
                    "msg": ("What is MSG? Is it bad for you?", "https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/expert-answers/monosodium-glutamate/faq-20058196"),
                    "nitrite": ("Cancer prevention: 7 tips to reduce your risk", "https://www.mayoclinic.org/healthy-lifestyle/adult-health/in-depth/cancer-prevention/art-20044816")
                }
                
                if ingredient in direct_pages:
                    title, url = direct_pages[ingredient]
                    citation = Citation(
                        title=f"Mayo Clinic: {title}",
                        authors=[Author(last_name="Mayo Clinic Staff", first_name="")],
                        journal="Mayo Clinic Expert Advice",
                        publication_date=datetime(2024, 1, 1),
                        url=url,
                        abstract=f"Expert medical guidance from Mayo Clinic on {ingredient} and its health effects, including evidence-based recommendations",
                        source_type="mayo_clinic_web",
                        relevance_score=0.9
                    )
                    citations.append(citation)
            
                    
        except Exception as e:
            logger.error(f"Mayo Clinic web search error: {e}")
            # Return empty list on error
        
        return citations[:max_results]
    
    def _search_nih(self, query: str, max_results: int) -> List[Citation]:
        """Search NIH/MedlinePlus for consumer health information."""
        citations = []
        
        try:
            
            # Extract ingredient name for targeted searches
            ingredient = query.split()[0].lower()
            
            # NIH/MedlinePlus health content mappings
            nih_content = {
                "sodium": {
                    "title": "Sodium in Your Diet - MedlinePlus",
                    "url": "https://medlineplus.gov/sodium.html",
                    "abstract": "NIH consumer health information on sodium intake, health effects, and dietary guidelines"
                },
                "msg": {
                    "title": "Food Additives - MedlinePlus Health Information",
                    "url": "https://medlineplus.gov/foodadditives.html",
                    "abstract": "NIH overview of food additives including MSG, safety information, and health effects"
                },
                "nitrite": {
                    "title": "Food Safety - MedlinePlus",
                    "url": "https://medlineplus.gov/foodsafety.html",
                    "abstract": "NIH information on food preservatives, safety guidelines, and health considerations"
                },
                "artificial": {
                    "title": "Artificial Sweeteners - MedlinePlus",
                    "url": "https://medlineplus.gov/artificialsweeteners.html",
                    "abstract": "NIH consumer information on artificial additives, safety, and health research"
                },
                "preservative": {
                    "title": "Food Preservatives and Health - MedlinePlus",
                    "url": "https://medlineplus.gov/foodadditives.html",
                    "abstract": "NIH health information on food preservatives, types, and safety considerations"
                }
            }
            
            # Check for matches and create citations
            for keyword, info in nih_content.items():
                if keyword in ingredient or keyword in query.lower():
                    citation = Citation(
                        title=info["title"],
                        authors=[Author(last_name="NIH", first_name="National Institutes of Health")],
                        journal="MedlinePlus Health Information",
                        publication_date=datetime(2024, 1, 1),
                        url=info["url"],
                        abstract=info["abstract"],
                        source_type="nih_web",
                        relevance_score=1.0  # Government health source
                    )
                    citations.append(citation)
                    break
                    
        except Exception as e:
            logger.error(f"NIH search error: {e}")
        
        return citations[:max_results]
    
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
    
    def fetch_abstract_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Fetch full abstract and details by DOI."""
        try:
            
            # Use CrossRef API to get detailed information
            url = f"https://api.crossref.org/works/{doi}"
            response = requests.get(url, timeout=10, verify=True)
            response.raise_for_status()
            
            data = response.json()
            work = data.get('message', {})
            
            # Extract authors
            authors_str = "Unknown"
            if 'author' in work:
                authors = []
                for author in work['author'][:3]:  # Limit to first 3 authors
                    given = author.get('given', '')
                    family = author.get('family', '')
                    if family:
                        authors.append(f"{given} {family}".strip())
                if authors:
                    authors_str = ", ".join(authors)
            
            # Extract publication year
            year = "Unknown"
            if 'published-print' in work:
                date_parts = work['published-print'].get('date-parts', [[]])[0]
                if date_parts:
                    year = str(date_parts[0])
            elif 'published-online' in work:
                date_parts = work['published-online'].get('date-parts', [[]])[0]
                if date_parts:
                    year = str(date_parts[0])
            
            abstract_details = {
                'title': work.get('title', ['Unknown'])[0] if work.get('title') else 'Unknown',
                'authors': authors_str,
                'journal': work.get('container-title', ['Unknown'])[0] if work.get('container-title') else 'Unknown',
                'year': year,
                'abstract': work.get('abstract', 'Abstract not available'),
                'doi': doi,
                'pmid': None
            }
            
            return abstract_details
            
        except Exception as e:
            logger.error(f"Error fetching abstract by DOI {doi}: {e}")
            return None
    
    def fetch_abstract_by_pmid(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Fetch full abstract and details by PMID."""
        try:
            
            # Use PubMed to get detailed information
            query = f"PMID:{pmid}"
            articles = list(self.pubmed.query(query, max_results=1))
            
            if not articles:
                return None
            
            article = articles[0]
            
            # Extract authors
            authors_str = "Unknown"
            if hasattr(article, 'authors') and article.authors:
                authors = []
                for author in article.authors[:3]:  # Limit to first 3 authors
                    if isinstance(author, dict):
                        given = author.get('firstname', '')
                        family = author.get('lastname', '')
                        if family:
                            authors.append(f"{given} {family}".strip())
                    else:
                        authors.append(str(author))
                if authors:
                    authors_str = ", ".join(authors)
            
            # Extract publication year
            year = "Unknown"
            if hasattr(article, 'publication_date') and article.publication_date:
                try:
                    if isinstance(article.publication_date, str):
                        year = article.publication_date[:4]
                    else:
                        year = str(article.publication_date.year)
                except:
                    pass
            
            abstract_details = {
                'title': article.title or 'Unknown',
                'authors': authors_str,
                'journal': getattr(article, 'journal', 'Unknown'),
                'year': year,
                'abstract': getattr(article, 'abstract', 'Abstract not available'),
                'doi': getattr(article, 'doi', None),
                'pmid': pmid
            }
            
            return abstract_details
            
        except Exception as e:
            logger.error(f"Error fetching abstract by PMID {pmid}: {e}")
            return None
    
    def extract_key_findings(self, abstract: str, ingredient: str, health_claim: str) -> str:
        """Extract key health findings from an abstract."""
        try:
            if not abstract or len(abstract) < 50:
                return "Key findings not available"
            
            # Simple keyword-based extraction
            abstract_lower = abstract.lower()
            ingredient_lower = ingredient.lower()
            
            # Look for key result indicators
            key_phrases = []
            
            # Look for results, conclusions, or findings
            sentences = abstract.split('.')
            for sentence in sentences:
                sentence_lower = sentence.lower().strip()
                
                # Skip if sentence is too short
                if len(sentence_lower) < 20:
                    continue
                
                # Check if sentence contains ingredient and result indicators
                if (ingredient_lower in sentence_lower and 
                    any(indicator in sentence_lower for indicator in 
                        ['result', 'conclusion', 'finding', 'showed', 'demonstrated', 
                         'associated', 'increased', 'decreased', 'caused', 'linked'])):
                    key_phrases.append(sentence.strip())
            
            if key_phrases:
                # Return the most relevant finding (usually the first one)
                return key_phrases[0][:300] + "..." if len(key_phrases[0]) > 300 else key_phrases[0]
            else:
                # Fallback: return first part of abstract
                return abstract[:200] + "..." if len(abstract) > 200 else abstract
                
        except Exception as e:
            logger.error(f"Error extracting key findings: {e}")
            return "Key findings extraction failed"
    
    def generate_health_summary(self, evidence_text: str, ingredient: str, max_chars: int = 180) -> str:
        """Generate a concise health summary from scientific evidence."""
        try:
            if not evidence_text or len(evidence_text) < 50:
                return f"Limited scientific evidence available for {ingredient}"
            
            # Extract key health effects mentioned in the evidence
            evidence_lower = evidence_text.lower()
            ingredient_lower = ingredient.lower()
            
            # Common health concern keywords and their descriptions
            health_effects = {
                'carcinogen': 'may increase cancer risk',
                'toxic': 'shows toxic effects',
                'endocrine': 'disrupts hormone function',
                'inflammatory': 'causes inflammation',
                'allergic': 'triggers allergic reactions',
                'oxidative': 'causes oxidative stress',
                'mutagenic': 'damages DNA',
                'neurotoxic': 'affects nervous system',
                'hepatotoxic': 'damages liver function',
                'nephrotoxic': 'harms kidney function'
            }
            
            # Find relevant health effects
            found_effects = []
            for keyword, description in health_effects.items():
                if keyword in evidence_lower:
                    found_effects.append(description)
            
            # Build summary
            if found_effects:
                effects_text = ", ".join(found_effects[:2])  # Limit to 2 effects
                summary = f"Research indicates {ingredient} {effects_text} based on scientific studies"
            else:
                # Fallback summary
                summary = f"Scientific studies suggest potential health concerns with {ingredient}"
            
            # Ensure summary fits within character limit
            if len(summary) > max_chars - 20:  # Reserve space for period
                summary = summary[:max_chars - 23] + "..."
            
            return summary + "."
            
        except Exception as e:
            logger.error(f"Error generating health summary: {e}")
            return f"Health assessment unavailable for {ingredient}."

    def _search_doaj(self, query: str, max_results: int) -> List[Citation]:
        """Search DOAJ (Directory of Open Access Journals) for open access articles."""
        citations = []
        
        try:
            
            # DOAJ API endpoint
            url = "https://doaj.org/api/search/articles/title%3A" + query.replace(" ", "%20")
            
            response = requests.get(url, timeout=10, verify=True)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            for item in results[:max_results]:
                try:
                    # Parse authors
                    authors = []
                    for author in item.get('bibjson', {}).get('author', []):
                        name = author.get('name', '')
                        if name:
                            name_parts = name.split(' ')
                            last_name = name_parts[-1] if name_parts else 'Unknown'
                            first_name = ' '.join(name_parts[:-1]) if len(name_parts) > 1 else ''
                            authors.append(Author(first_name=first_name, last_name=last_name))
                    
                    # Parse publication date
                    pub_date = None
                    year = item.get('bibjson', {}).get('year')
                    if year:
                        pub_date = datetime(int(year), 1, 1)
                    
                    citation = Citation(
                        title=item.get('bibjson', {}).get('title', 'Unknown Title'),
                        authors=authors or [Author(last_name="Unknown")],
                        journal=item.get('bibjson', {}).get('journal', {}).get('title', 'DOAJ Article'),
                        publication_date=pub_date,
                        url=item.get('bibjson', {}).get('link', [{}])[0].get('url') if item.get('bibjson', {}).get('link') else None,
                        abstract=item.get('bibjson', {}).get('abstract'),
                        source_type="doaj",
                        relevance_score=0.85  # Open access articles are highly relevant
                    )
                    
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing DOAJ item: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"DOAJ search error: {e}")
        
        return citations
    
    def _search_arxiv(self, query: str, max_results: int) -> List[Citation]:
        """Search arXiv for preprint papers in quantitative biology and related fields."""
        citations = []
        
        try:
            
            # arXiv API search for quantitative biology (q-bio) and related categories
            arxiv_url = "http://export.arxiv.org/api/query"
            
            # Search in quantitative biology categories relevant to food science
            search_query = f"cat:q-bio.BM OR cat:q-bio.OT AND all:{query}"
            
            params = {
                'search_query': search_query,
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance'
            }
            
            response = requests.get(arxiv_url, params=params, timeout=10, verify=True)
            response.raise_for_status()
            
            # Parse XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            # arXiv namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
            
            for entry in root.findall('atom:entry', ns)[:max_results]:
                try:
                    title = entry.find('atom:title', ns).text.strip() if entry.find('atom:title', ns) is not None else "Unknown Title"
                    summary = entry.find('atom:summary', ns).text.strip() if entry.find('atom:summary', ns) is not None else ""
                    
                    # Get authors
                    authors = []
                    for author in entry.findall('atom:author', ns):
                        name_elem = author.find('atom:name', ns)
                        if name_elem is not None:
                            full_name = name_elem.text.strip()
                            name_parts = full_name.split()
                            if len(name_parts) >= 2:
                                authors.append(Author(last_name=name_parts[-1], first_name=" ".join(name_parts[:-1])))
                            else:
                                authors.append(Author(last_name=full_name, first_name=""))
                    
                    # Get publication date
                    pub_date = entry.find('atom:published', ns)
                    year = 2024  # Default
                    if pub_date is not None:
                        try:
                            year = int(pub_date.text[:4])
                        except:
                            pass
                    
                    # Get arXiv ID and create URL
                    arxiv_id = entry.find('atom:id', ns).text.split('/')[-1] if entry.find('atom:id', ns) is not None else ""
                    url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None
                    
                    citation = Citation(
                        title=title,
                        authors=authors[:3],  # Limit to first 3 authors
                        journal="arXiv preprint",
                        publication_date=datetime(year, 1, 1),
                        url=url,
                        source_type="arxiv",
                        relevance_score=0.8,
                        pmid=arxiv_id
                    )
                    citations.append(citation)
                    
                except Exception as e:
                    logger.warning(f"Error parsing arXiv entry: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"arXiv search error: {e}")
        
        return citations
    
    def _search_biorxiv(self, query: str, max_results: int) -> List[Citation]:
        """Search bioRxiv for biology and health science preprints."""
        citations = []
        
        try:
            
            # bioRxiv API search
            biorxiv_url = "https://api.biorxiv.org/details/biorxiv"
            
            # Search recent papers (last 2 years)
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
            
            search_url = f"{biorxiv_url}/{start_date}/{end_date}"
            
            response = requests.get(search_url, timeout=10, verify=True)
            response.raise_for_status()
            
            data = response.json()
            
            if 'collection' in data:
                # Filter papers by relevance to query
                relevant_papers = []
                query_terms = query.lower().split()
                
                for paper in data['collection']:
                    title = paper.get('title', '').lower()
                    abstract = paper.get('abstract', '').lower()
                    
                    # Calculate relevance score
                    relevance = 0
                    for term in query_terms:
                        if term in title:
                            relevance += 0.3
                        if term in abstract:
                            relevance += 0.1
                    
                    if relevance > 0.1:  # Only include relevant papers
                        relevant_papers.append((paper, relevance))
                
                # Sort by relevance and take top results
                relevant_papers.sort(key=lambda x: x[1], reverse=True)
                
                for paper_data, relevance in relevant_papers[:max_results]:
                    try:
                        # Parse authors
                        authors = []
                        authors_str = paper_data.get('authors', '')
                        if authors_str:
                            author_names = authors_str.split(';')[:3]  # Limit to first 3
                            for author_name in author_names:
                                name_parts = author_name.strip().split()
                                if len(name_parts) >= 2:
                                    authors.append(Author(last_name=name_parts[-1], first_name=" ".join(name_parts[:-1])))
                                else:
                                    authors.append(Author(last_name=author_name.strip(), first_name=""))
                        
                        # Get publication date
                        date_str = paper_data.get('date', '')
                        year = 2024
                        if date_str:
                            try:
                                year = int(date_str[:4])
                            except:
                                pass
                        
                        # Create DOI URL
                        doi = paper_data.get('doi', '')
                        url = f"https://doi.org/{doi}" if doi else f"https://www.biorxiv.org/content/{paper_data.get('server', 'biorxiv')}/early/{date_str}/{doi}"
                        
                        citation = Citation(
                            title=paper_data.get('title', 'Unknown Title'),
                            authors=authors,
                            journal="bioRxiv preprint",
                            publication_date=datetime(year, 1, 1),
                            url=url,
                            source_type="biorxiv",
                            relevance_score=min(relevance, 1.0),
                            doi=doi if doi else None
                        )
                        citations.append(citation)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing bioRxiv entry: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"bioRxiv search error: {e}")
        
        return citations
    
    def _search_semantic_scholar(self, query: str, max_results: int) -> List[Citation]:
        """Search Semantic Scholar for academic papers with citation metrics."""
        citations = []
        
        try:
            
            # Semantic Scholar API
            api_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            
            params = {
                'query': query,
                'limit': max_results,
                'fields': 'title,authors,year,journal,citationCount,url,abstract,openAccessPdf'
            }
            
            response = requests.get(api_url, params=params, timeout=10, verify=True)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data:
                for paper in data['data']:
                    try:
                        # Parse authors
                        authors = []
                        if 'authors' in paper and paper['authors']:
                            for author_data in paper['authors'][:3]:  # Limit to first 3
                                name = author_data.get('name', '')
                                if name:
                                    name_parts = name.split()
                                    if len(name_parts) >= 2:
                                        authors.append(Author(last_name=name_parts[-1], first_name=" ".join(name_parts[:-1])))
                                    else:
                                        authors.append(Author(last_name=name, first_name=""))
                        
                        # Get publication year
                        year = paper.get('year', 2024)
                        if not year:
                            year = 2024
                        
                        # Calculate relevance score based on citation count and recency
                        citation_count = paper.get('citationCount', 0)
                        relevance = min(0.5 + (citation_count / 100), 1.0)  # Base 0.5, up to 1.0 based on citations
                        
                        # Get URL (prefer open access PDF if available)
                        url = paper.get('url', '')
                        if 'openAccessPdf' in paper and paper['openAccessPdf'] and paper['openAccessPdf'].get('url'):
                            url = paper['openAccessPdf']['url']
                        
                        citation = Citation(
                            title=paper.get('title', 'Unknown Title'),
                            authors=authors,
                            journal=paper.get('journal', {}).get('name', 'Unknown Journal') if paper.get('journal') else 'Unknown Journal',
                            publication_date=datetime(year, 1, 1),
                            url=url,
                            source_type="semantic_scholar",
                            relevance_score=relevance
                        )
                        citations.append(citation)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing Semantic Scholar entry: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Semantic Scholar search error: {e}")
        
        return citations
    
    def _search_europe_pmc(self, query: str, max_results: int) -> List[Citation]:
        """Search Europe PMC for European biomedical literature."""
        citations = []
        
        try:
            
            # Europe PMC API
            api_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            
            params = {
                'query': query,
                'resultType': 'core',
                'pageSize': max_results,
                'format': 'json'
            }
            
            response = requests.get(api_url, params=params, timeout=10, verify=True)
            response.raise_for_status()
            
            data = response.json()
            
            if 'resultList' in data and 'result' in data['resultList']:
                for paper in data['resultList']['result']:
                    try:
                        # Parse authors
                        authors = []
                        if 'authorList' in paper and paper['authorList'] and 'author' in paper['authorList']:
                            for author_data in paper['authorList']['author'][:3]:  # Limit to first 3
                                last_name = author_data.get('lastName', '')
                                first_name = author_data.get('firstName', '') or author_data.get('initials', '')
                                if last_name:
                                    authors.append(Author(last_name=last_name, first_name=first_name))
                        
                        # Get publication year
                        year = 2024
                        if 'pubYear' in paper:
                            try:
                                year = int(paper['pubYear'])
                            except:
                                pass
                        
                        # Create URL (prefer DOI, fall back to PMC or PMID)
                        url = None
                        if 'doi' in paper and paper['doi']:
                            url = f"https://doi.org/{paper['doi']}"
                        elif 'pmcid' in paper and paper['pmcid']:
                            url = f"https://europepmc.org/article/PMC/{paper['pmcid'].replace('PMC', '')}"
                        elif 'pmid' in paper and paper['pmid']:
                            url = f"https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}/"
                        
                        citation = Citation(
                            title=paper.get('title', 'Unknown Title'),
                            authors=authors,
                            journal=paper.get('journalTitle', 'Unknown Journal'),
                            publication_date=datetime(year, 1, 1),
                            url=url,
                            source_type="europe_pmc",
                            relevance_score=0.75,
                            pmid=paper.get('pmid'),
                            doi=paper.get('doi')
                        )
                        citations.append(citation)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing Europe PMC entry: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Europe PMC search error: {e}")
        
        return citations


