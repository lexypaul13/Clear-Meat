# 🚀 Apply RLS Performance Optimization

## Instructions

1. **Go to Supabase SQL Editor:**
   https://supabase.com/dashboard/project/ksgxendfsejkxhrmfsbi/sql/new

2. **Copy and paste the migration SQL:**
   - Open file: `supabase/migrations/20250730_optimize_rls_performance.sql`
   - Copy ALL contents (162 lines)
   - Paste into SQL Editor

3. **Run the SQL:**
   - Click "Run" button
   - Should see "Success. No rows returned" message

## What This Fixes

### Performance Issues Resolved:
✅ **10 RLS Initplan Issues** - Auth functions now evaluate once per query instead of per row
✅ **35+ Duplicate Policies** - Consolidated overlapping policies to reduce overhead

### Expected Performance Improvements:
- **10x-100x faster** queries on large datasets
- **Better query plans** from PostgreSQL optimizer  
- **Improved scalability** as your product database grows
- **Reduced CPU usage** on database queries

## Verification

After applying, run this query to verify the optimization worked:

```sql
-- Check that policies were consolidated (should be fewer policies now)
SELECT schemaname, tablename, COUNT(*) as policy_count
FROM pg_policies 
WHERE schemaname = 'public'
AND tablename IN ('ai_analysis_cache', 'description_cache', 'ingredients', 'product_alternatives', 'product_ingredients')
GROUP BY schemaname, tablename
ORDER BY tablename;

-- Should see ~4 policies per table instead of many duplicates
```

## Testing

After applying:
1. Test your iOS app's Explore endpoint
2. Verify product scanning still works  
3. Check that user authentication functions properly
4. Confirm OpenFoodFacts fallback still works

All functionality should be identical - only performance is improved!

## Rollback (if needed)

If any issues occur, the original policies are preserved in previous migration files and can be restored.