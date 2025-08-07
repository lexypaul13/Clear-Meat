"""
AI-powered ingredient analysis service using LangChain.
Provides detailed health analysis and multi-source citations for individual ingredients.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from app.services.gemini_service import GeminiService
# from app.services.citation_tools import CitationSearchService  # Disabled - using Google Search grounding
from app.models.citation import CitationSearch

logger = logging.getLogger(__name__)


class IngredientAnalysis(BaseModel):
    """Structured ingredient analysis response."""
    ingredient: str
    description: str = Field(description="What this ingredient is and its purpose in food")
    health_concerns: List[str] = Field(description="Specific health risks associated with this ingredient")
    mechanism: str = Field(description="How this ingredient affects the body")
    risk_level: str = Field(description="low, moderate, or high")
    recommended_action: str = Field(description="Advice for consumers")
    search_terms: List[str] = Field(description="Key terms for finding relevant research")


class IngredientCitation(BaseModel):
    """Citation with relevance scoring."""
    title: str
    source: str
    url: str
    year: Optional[int] = None
    source_type: str  # "academic", "health_authority", "regulatory"
    user_friendly: bool = Field(description="Whether this source is accessible to general public")
    relevance_score: float = Field(description="0-1 relevance to the specific ingredient")


class IngredientAnalysisService:
    """AI-powered ingredient analysis with multi-source citations."""
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.citation_service = CitationSearchService()
        
    async def analyze_ingredient(self, ingredient: str) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of a food ingredient.
        
        Args:
            ingredient: Name of the ingredient to analyze
            
        Returns:
            Dict containing analysis, citations, and recommendations
        """
        try:
            logger.info(f"[Ingredient Analysis] Starting analysis for: {ingredient}")
            
            # Step 1: Generate AI analysis
            analysis = await self._generate_ingredient_analysis(ingredient)
            if not analysis:
                return self._create_fallback_response(ingredient)
            
            # Step 2: Search for citations using AI-generated terms
            citations = await self._search_multi_source_citations(
                ingredient, 
                analysis.search_terms
            )
            
            # Step 3: Filter and score citations for relevance
            relevant_citations = self._filter_and_score_citations(
                citations, 
                ingredient, 
                analysis.health_concerns
            )
            
            return {
                "ingredient": ingredient,
                "analysis": {
                    "description": analysis.description,
                    "health_concerns": analysis.health_concerns,
                    "mechanism": analysis.mechanism,
                    "risk_level": analysis.risk_level,
                    "recommended_action": analysis.recommended_action
                },
                "citations": {
                    "scientific_evidence": [c for c in relevant_citations if c["source_type"] == "academic"],
                    "health_guidance": [c for c in relevant_citations if c["source_type"] in ["health_authority", "regulatory"]],
                    "total_found": len(relevant_citations)
                },
                "metadata": {
                    "analysis_timestamp": "2025-01-31",
                    "sources_searched": ["pubmed", "fda", "mayo_clinic", "harvard_health", "cdc"],
                    "confidence": "high" if len(relevant_citations) >= 3 else "moderate"
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing ingredient {ingredient}: {e}")
            return self._create_error_response(ingredient, str(e))
    
    async def _generate_ingredient_analysis(self, ingredient: str) -> Optional[IngredientAnalysis]:
        """Generate structured ingredient analysis using Gemini AI."""
        try:
            prompt = f"""
            Analyze the food ingredient: "{ingredient}"
            
            Provide a comprehensive analysis focusing on:
            
            1. DESCRIPTION: What is this ingredient? What's its chemical nature and purpose in food processing?
            
            2. HEALTH CONCERNS: List specific health risks associated with THIS ingredient (not general food safety):
               - Be specific to this ingredient, not generic categories
               - Include both established risks and emerging concerns
               - Mention vulnerable populations if relevant
            
            3. MECHANISM: How does this ingredient affect the human body? What biological processes does it impact?
            
            4. RISK LEVEL: Classify as "low", "moderate", or "high" based on current scientific evidence
            
            5. RECOMMENDED ACTION: Practical advice for consumers (avoid, limit, monitor, etc.)
            
            6. SEARCH TERMS: Generate 3-5 specific search terms that would find the most relevant research about this ingredient's health effects
            
            Focus on THIS SPECIFIC INGREDIENT, not broad categories. Be evidence-based and specific.
            
            Format your response as JSON with these exact keys:
            {{
                "description": "...",
                "health_concerns": ["concern1", "concern2", ...],
                "mechanism": "...",
                "risk_level": "low|moderate|high",
                "recommended_action": "...",
                "search_terms": ["term1", "term2", ...]
            }}
            """
            
            response = await self.gemini_service.generate_response_async(prompt)
            
            # Parse JSON response
            import json
            try:
                data = json.loads(response)
                return IngredientAnalysis(
                    ingredient=ingredient,
                    description=data["description"],
                    health_concerns=data["health_concerns"],
                    mechanism=data["mechanism"],
                    risk_level=data["risk_level"],
                    recommended_action=data["recommended_action"],
                    search_terms=data["search_terms"]
                )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse AI response as JSON: {e}")
                return self._parse_unstructured_response(response, ingredient)
                
        except Exception as e:
            logger.error(f"Error generating AI analysis for {ingredient}: {e}")
            return None
    
    def _parse_unstructured_response(self, response: str, ingredient: str) -> IngredientAnalysis:
        """Fallback parser for unstructured AI responses."""
        # Simple fallback - extract key information
        return IngredientAnalysis(
            ingredient=ingredient,
            description=f"Analysis of {ingredient} as a food ingredient",
            health_concerns=["Requires further research"],
            mechanism="Mechanism of action under investigation",
            risk_level="moderate",
            recommended_action="Consume in moderation pending further research",
            search_terms=[f"{ingredient} food additive", f"{ingredient} health effects", f"{ingredient} safety"]
        )
    
    async def _search_multi_source_citations(
        self, 
        ingredient: str, 
        search_terms: List[str]
    ) -> List[Dict[str, Any]]:
        """Search multiple citation sources with AI-generated terms."""
        all_citations = []
        
        # Combine ingredient name with AI-generated search terms
        enhanced_search_terms = [
            f"{ingredient} {term}" for term in search_terms[:3]  # Limit to top 3 terms
        ]
        
        # Search each enhanced term
        for search_query in enhanced_search_terms:
            try:
                # Search academic sources
                academic_params = CitationSearch(
                    ingredient=ingredient,
                    health_claim=" ".join(search_terms),
                    max_results=2,
                    search_pubmed=True,
                    search_crossref=True
                )
                
                # Search health authority sources
                authority_params = CitationSearch(
                    ingredient=ingredient,
                    health_claim=" ".join(search_terms),
                    max_results=2,
                    search_fda=True,
                    search_cdc=True,
                    search_mayo_clinic=True,
                    search_harvard_health=True,
                    search_nih=True
                )
                
                # Execute searches in parallel
                academic_result = self.citation_service.search_citations(academic_params)
                authority_result = self.citation_service.search_citations(authority_params)
                
                # Combine results
                if academic_result.citations:
                    for citation in academic_result.citations:
                        all_citations.append({
                            "title": citation.title,
                            "source": citation.journal or citation.source_type,
                            "url": citation.url or "",
                            "year": citation.publication_date.year if citation.publication_date else None,
                            "source_type": "academic",
                            "user_friendly": False
                        })
                
                if authority_result.citations:
                    for citation in authority_result.citations:
                        all_citations.append({
                            "title": citation.title,
                            "source": citation.journal or citation.source_type,
                            "url": citation.url or "",
                            "year": citation.publication_date.year if citation.publication_date else None,
                            "source_type": "health_authority" if "fda" in citation.source_type.lower() or "cdc" in citation.source_type.lower() else "health_authority",
                            "user_friendly": True
                        })
                
            except Exception as e:
                logger.warning(f"Citation search failed for '{search_query}': {e}")
                continue
        
        return all_citations
    
    def _filter_and_score_citations(
        self, 
        citations: List[Dict[str, Any]], 
        ingredient: str, 
        health_concerns: List[str]
    ) -> List[Dict[str, Any]]:
        """Filter and score citations for relevance to the specific ingredient."""
        if not citations:
            return []
        
        scored_citations = []
        seen_urls = set()
        
        for citation in citations:
            # Skip duplicates
            if citation["url"] in seen_urls:
                continue
            seen_urls.add(citation["url"])
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(
                citation, ingredient, health_concerns
            )
            
            # Only include citations with reasonable relevance
            if relevance_score >= 0.3:
                citation["relevance_score"] = relevance_score
                scored_citations.append(citation)
        
        # Sort by relevance score (descending)
        scored_citations.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Return top 8 most relevant citations
        return scored_citations[:8]
    
    def _calculate_relevance_score(
        self, 
        citation: Dict[str, Any], 
        ingredient: str, 
        health_concerns: List[str]
    ) -> float:
        """Calculate relevance score (0-1) for a citation."""
        score = 0.0
        title_lower = citation["title"].lower()
        ingredient_lower = ingredient.lower()
        
        # Exact ingredient name match in title (high value)
        if ingredient_lower in title_lower:
            score += 0.5
        
        # Partial ingredient match (moderate value)
        ingredient_words = ingredient_lower.split()
        for word in ingredient_words:
            if len(word) > 3 and word in title_lower:
                score += 0.2
        
        # Health concern keywords in title
        for concern in health_concerns:
            concern_words = concern.lower().split()
            for word in concern_words:
                if len(word) > 4 and word in title_lower:
                    score += 0.1
        
        # Source type bonuses
        if citation["source_type"] == "health_authority":
            score += 0.1  # Bonus for authoritative sources
        
        # Recency bonus (if year available)
        if citation.get("year") and citation["year"] >= 2020:
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _create_fallback_response(self, ingredient: str) -> Dict[str, Any]:
        """Create fallback response when AI analysis fails."""
        return {
            "ingredient": ingredient,
            "analysis": {
                "description": f"Food ingredient analysis for {ingredient}",
                "health_concerns": ["Limited research available"],
                "mechanism": "Mechanism of action requires further study",
                "risk_level": "unknown",
                "recommended_action": "Consult healthcare provider for specific concerns"
            },
            "citations": {
                "scientific_evidence": [],
                "health_guidance": [],
                "total_found": 0
            },
            "metadata": {
                "analysis_timestamp": "2025-01-31",
                "confidence": "low",
                "note": "AI analysis unavailable, showing fallback information"
            }
        }
    
    def _create_error_response(self, ingredient: str, error: str) -> Dict[str, Any]:
        """Create error response."""
        return {
            "ingredient": ingredient,
            "error": f"Analysis failed: {error}",
            "analysis": None,
            "citations": None,
            "metadata": {
                "analysis_timestamp": "2025-01-31",
                "status": "error"
            }
        }