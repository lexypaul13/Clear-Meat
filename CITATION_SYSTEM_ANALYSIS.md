# Citation System Analysis & Solution

## Problem Statement
**Apple App Store Rejection (Guideline 1.4.1 - Safety - Physical Harm)**
- Medical information lacks accurate, corresponding citations for ingredients
- Generic citations from `vertexaisearch.cloud.google.com` instead of authoritative medical sources
- Citations pointing to non-medical sources (TikTok, OpenFoodFacts, blogs)

## Current Implementation Issues
### Gemini + Google Search Grounding Limitations
- **Inconsistent Source Quality**: Despite prompt engineering, still returns generic/irrelevant sources
- **URL Redirect Problems**: Citations go through Google redirect URLs that don't resolve to intended medical sites
- **Limited Control**: Cannot guarantee medical authority sources despite extensive filtering
- **Prompt Dependency**: Relies heavily on Gemini following complex prompt instructions

### What We've Tried
1. ✅ **Enhanced Prompt Engineering** - Specific `site:` searches for medical authorities
2. ✅ **Domain Filtering** - Whitelist/blacklist system for reputable sources
3. ✅ **URL Resolution** - Resolve Google redirects to final destinations
4. ✅ **Fallback Citations** - Guarantee citations always present
5. ✅ **Code Cleanup** - Removed 18% of obsolete code
6. ❌ **DuckDuckGo Integration** - Failed due to compatibility issues

## Proposed Solution: Dual-LLM Architecture

### Primary: Perplexity API for Citations
```
Health Assessment Flow:
1. Gemini 1.5 Pro → Ingredient analysis & health assessment
2. Perplexity API → Medical citations for high-risk ingredients
3. Merge results → Final response with authoritative citations
```

### Benefits
- **Native Medical Research**: Perplexity designed for research with automatic citations
- **Higher Quality Sources**: Better at finding authoritative medical literature
- **Real-time Web Search**: No redirect URL issues
- **Cost Effective**: Use Perplexity only for citation-critical requests

### Implementation Plan
1. Create `PerplexityCitationService` class
2. Integrate with existing `HealthAssessmentMCPService`
3. Use Perplexity for top 3 high-risk ingredients only
4. Maintain Gemini for core health assessment logic

## Expected Outcome
- ✅ Apple App Store compliance with authoritative medical citations
- ✅ Maintain current assessment quality and performance
- ✅ Cost-effective hybrid approach (Gemini + Perplexity)
- ✅ Reliable, consistent citation generation

## Test Products
- `0006345049070` - Processed meat with preservatives
- `00073455` - High sodium content
- `00084215` - Multiple additives and preservatives
