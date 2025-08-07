# Citation Services Disabled

## Why these services were disabled:

The following citation services have been disabled due to reliability issues:
- `citation_tools.py` → `citation_tools.py.disabled`
- `async_citation_search.py` → `async_citation_search.py.disabled`

### Problems encountered:
1. **CrossRef API**: Frequent timeouts (10+ seconds)
2. **PubMed API**: Connection failures and timeouts
3. **Semantic Scholar**: Rate limiting (429 errors)
4. **Overall**: 70-80% failure rate, adding 10-30 seconds to requests

### Replacement:
These services have been replaced with **Gemini's Google Search grounding**, which provides:
- 95%+ reliability
- Access to government health sites (FDA, CDC, NIH)
- Medical institutions (Mayo Clinic, Cleveland Clinic)
- Reputable health blogs and evidence-based nutrition sites
- Real-time information with automatic citations

### To re-enable:
1. Uncomment dependencies in `requirements.txt`:
   - `crossref-commons==0.0.7`
   - `pymed==0.8.9`
2. Rename files back to `.py` extension
3. Re-enable imports in health assessment services

### Cost consideration:
Google Search grounding costs $35 per 1,000 queries, but with aggressive caching at the ingredient level, the effective cost is minimal.