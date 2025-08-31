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

## **CRITICAL ISSUE: Gemini Assessment Failures**

### **Backend Logs Show System Failure:**
```
[ERROR] Assessment returned None/empty result
[INFO] Creating direct assessment from categorization with 0 high-risk, 5 moderate-risk
[INFO] Final ingredients: 0 high-risk, 5 moderate-risk, 5 low-risk
```

### **Root Cause Analysis:**
1. **Gemini Inconsistency**: Sometimes works, sometimes returns `None/empty result`
2. **Fallback Without Citations**: System falls back to basic categorization with `citations: []`
3. **iOS Receives Empty**: Frontend gets ingredients with no citations
4. **User Sees Nothing**: No citations displayed despite backend "success"

### **Gemini vs Perplexity Comparison:**

| Issue | Gemini (Current) | Perplexity (Proposed) |
|-------|------------------|----------------------|
| **Reliability** | ❌ Inconsistent, fails silently | ✅ Consistent citation generation |
| **Complexity** | ❌ Complex JSON prompting, grounding metadata | ✅ Simple question → answer with citations |
| **Medical Focus** | ❌ Generic web search with filtering | ✅ Built for research with medical authorities |
| **Implementation** | ❌ 8+ steps: prompt → parse → filter → resolve → map | ✅ 2 steps: ask → receive citations |
| **Maintenance** | ❌ Complex prompt engineering, domain lists | ✅ Minimal maintenance required |

## Proposed Solution: Hybrid Architecture

### **Approach: Best of Both Worlds**
```
Health Assessment Flow:
1. Gemini 1.5 Pro → Ingredient categorization (what it does well)
2. Perplexity API → Medical citations for high-risk ingredients (what it does best)
3. Merge results → Reliable response with authoritative citations
```

### **Why This Works:**
- **Gemini**: Excellent at ingredient analysis and categorization
- **Perplexity**: Excellent at research and citation generation
- **Combined**: Reliable system using each AI's strengths

### **Implementation Benefits:**
- ✅ **Simpler Code**: Less complex than current Gemini-only approach
- ✅ **More Reliable**: Perplexity specializes in citations
- ✅ **Cost Effective**: Use Perplexity only for citation-critical requests
- ✅ **Apple Compliant**: Consistent, authoritative medical citations

### Implementation Plan
1. Create `PerplexityCitationService` class
2. Integrate with existing `HealthAssessmentMCPService`
3. Use Perplexity for top 3 high-risk ingredients only
4. Maintain Gemini for core health assessment logic

## Expected Outcome
- ✅ Apple App Store compliance with authoritative medical citations
- ✅ Maintain current assessment quality and performance
- ✅ Cost-effective hybrid approach (Gemini + Perplexity)
- ✅ **Reliable, consistent citation generation** (solving current failures)

## Test Products
- `0006345049070` - Processed meat with preservatives
- `00073455` - High sodium content
- `00084215` - Multiple additives and preservatives
- `00080897` - Current failing product (Ghee, Salt, Chili, Nuts, Yogurt)
