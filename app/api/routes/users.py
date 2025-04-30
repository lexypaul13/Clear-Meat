"""User routes for the MeatWise API."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.db.supabase import get_supabase

router = APIRouter()

class UserPreferences(BaseModel):
    """User preferences model with fields matching onboarding process."""
    # Screen 1: Nutrition Priorities
    nutrition_focus: Optional[str] = None  # "protein", "fat", "salt"
    
    # Screen 2: Additives and Preservatives
    avoid_preservatives: Optional[bool] = None  # True/False
    
    # Screen 3: Antibiotics and Hormones in Raising
    prefer_antibiotic_free: Optional[bool] = None  # True/False
    
    # Screen 4: Sourcing & Animal Diet
    prefer_grass_fed: Optional[bool] = None  # True/False
    
    # Screen 5: Typical Cooking Style
    cooking_style: Optional[str] = None  # "grilling", "pan_frying", "oven_slow_cooker"
    
    # Screen 6: Openness to Meat Alternatives
    open_to_alternatives: Optional[bool] = None  # True/False
    
    # Legacy fields (keeping for backward compatibility)
    dietary_preferences: Optional[List[str]] = None
    cooking_experience: Optional[str] = None
    meat_preferences: Optional[List[str]] = None

class UserHistory(BaseModel):
    """User history model."""
    product_id: int
    viewed_at: str

@router.get("/preferences")
async def get_preferences():
    """Get user preferences."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        response = supabase.table('profiles').select(
            'preferences'
        ).eq('id', user.id).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        return {"preferences": response.data.get("preferences", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preferences")
async def save_preferences(preferences: UserPreferences):
    """Save user preferences."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        response = supabase.table('profiles').update({
            "preferences": preferences.model_dump(exclude_none=True)
        }).eq('id', user.id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        return {"preferences": response.data[0]["preferences"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendations")
async def get_recommendations():
    """Get personalized product recommendations based on new preference model."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        # Get user preferences
        profile = supabase.table('profiles').select(
            'preferences'
        ).eq('id', user.id).single().execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        preferences = profile.data.get("preferences", {})
        
        # Build query conditions based on new preferences model
        query = supabase.table('products').select('*')
        
        # Apply filters based on nutrition focus
        nutrition_focus = preferences.get("nutrition_focus")
        if nutrition_focus == "protein":
            query = query.order('protein', desc=True)
        elif nutrition_focus == "fat":
            query = query.order('fat')
        elif nutrition_focus == "salt":
            query = query.order('salt')
            
        # Apply filters for additives and preservatives
        if preferences.get("avoid_preservatives") is True:
            query = query.eq('contains_preservatives', False)
            
        # Apply filters for antibiotics/hormones
        if preferences.get("prefer_antibiotic_free") is True:
            query = query.eq('antibiotic_free', True)
            query = query.eq('hormone_free', True)
            
        # Apply filters for grass-fed/pasture-raised
        if preferences.get("prefer_grass_fed") is True:
            query = query.eq('pasture_raised', True)
            
        # Legacy: Consider meat preferences if no new preferences set
        meat_preferences = preferences.get("meat_preferences", [])
        if meat_preferences and not any([
            nutrition_focus, 
            preferences.get("avoid_preservatives"), 
            preferences.get("prefer_antibiotic_free"),
            preferences.get("prefer_grass_fed")
        ]):
            query = query.in_('meat_type', meat_preferences)
            
        # Get results
        response = query.limit(4).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history():
    """Get user's product viewing history."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        response = supabase.table('user_history').select(
            'products(*)'
        ).eq('user_id', user.id).order('viewed_at', desc=True).limit(5).execute()
        
        return [item["products"] for item in response.data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/history")
async def add_to_history(history: UserHistory):
    """Add a product to user's viewing history."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        response = supabase.table('user_history').insert({
            "user_id": user.id,
            "product_id": history.product_id,
            "viewed_at": history.viewed_at
        }).execute()
        
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/explore")
async def get_ai_recommendations():
    """Get personalized product recommendations using rule-based weighted scoring."""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user()
        
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        # Get user preferences 
        profile = supabase.table('profiles').select('preferences').eq('id', user.id).single().execute()
        
        if not profile.data:
            raise HTTPException(status_code=404, detail="Profile not found")
            
        preferences = profile.data.get("preferences", {})
        
        # Get maximum values for normalization
        try:
            max_values = supabase.rpc('get_product_max_values').execute()
            if max_values.data:
                max_protein = max_values.data.get("max_protein", 100)
                max_fat = max_values.data.get("max_fat", 100)
                max_salt = max_values.data.get("max_salt", 100)
            else:
                # Fallback values if the RPC returned no data
                max_protein = 100
                max_fat = 100
                max_salt = 100
        except:
            # Fallback values if the RPC call failed
            max_protein = 100
            max_fat = 100
            max_salt = 100
            
            # Log that we're using fallback values
            print("Warning: Using fallback normalization values. Please run the DB migration.")
        
        # Initialize default weights
        weights = {
            "w_protein": 0.15,
            "w_fat": 0.15, 
            "w_sodium": 0.15,
            "w_antibiotic": 0.15,
            "w_grass": 0.2,
            "w_preservatives": 0.2
        }
        
        # Adjust weights based on user preferences
        nutrition_focus = preferences.get("nutrition_focus")
        if nutrition_focus == "protein":
            weights["w_protein"] = 0.4
            weights["w_fat"] = 0.1
            weights["w_sodium"] = 0.1
        elif nutrition_focus == "fat":
            weights["w_protein"] = 0.1
            weights["w_fat"] = 0.4
            weights["w_sodium"] = 0.1
        elif nutrition_focus == "salt":
            weights["w_protein"] = 0.1
            weights["w_fat"] = 0.1
            weights["w_sodium"] = 0.4
        
        # Adjust weights based on other preferences
        if preferences.get("prefer_antibiotic_free"):
            weights["w_antibiotic"] = 0.25
            
        if preferences.get("prefer_grass_fed"):
            weights["w_grass"] = 0.25
            
        if preferences.get("avoid_preservatives"):
            weights["w_preservatives"] = 0.25
        
        try:
            # Try to use the execute_sql RPC function for weighted scoring
            query = """
            SELECT 
              code, 
              name, 
              brand,
              description,
              protein,
              fat,
              salt,
              meat_type,
              image_url,
              antibiotic_free,
              pasture_raised,
              contains_preservatives,
              
              -- Compute weighted score
              (GREATEST(0, LEAST(1, CAST(protein AS FLOAT) / {max_protein})) * {w_protein}) +
              (GREATEST(0, LEAST(1, 1 - (CAST(fat AS FLOAT) / {max_fat}))) * {w_fat}) +
              (GREATEST(0, LEAST(1, 1 - (CAST(salt AS FLOAT) / {max_salt}))) * {w_sodium}) +
              (CASE WHEN antibiotic_free THEN {w_antibiotic} ELSE 0 END) +
              (CASE WHEN pasture_raised THEN {w_grass} ELSE 0 END) +
              (CASE WHEN NOT contains_preservatives THEN {w_preservatives} ELSE 0 END) AS score
              
            FROM products
            WHERE protein IS NOT NULL AND fat IS NOT NULL AND salt IS NOT NULL
            ORDER BY score DESC
            LIMIT 10
            """.format(
                max_protein=max_protein,
                max_fat=max_fat,
                max_salt=max_salt,
                w_protein=weights["w_protein"],
                w_fat=weights["w_fat"],
                w_sodium=weights["w_sodium"],
                w_antibiotic=weights["w_antibiotic"],
                w_grass=weights["w_grass"],
                w_preservatives=weights["w_preservatives"]
            )
            
            result = supabase.rpc('execute_sql', {'sql_query': query}).execute()
            if result.data:
                products = result.data
            else:
                # Fallback if RPC returns no data
                raise Exception("No data returned from SQL execution")
        except:
            # Fallback to basic query approach if the RPC is not available
            print("Warning: Using fallback query method. Please run the DB migration.")
            
            # Get all products
            result = supabase.table('products').select('*').execute()
            all_products = result.data
            
            # Compute scores manually in Python
            scored_products = []
            for product in all_products:
                # Skip products with missing nutritional values
                if product.get("protein") is None or product.get("fat") is None or product.get("salt") is None:
                    continue
                
                # Calculate normalized values
                protein_norm = min(1, max(0, product.get("protein", 0) / max_protein))
                fat_norm = min(1, max(0, 1 - (product.get("fat", 0) / max_fat)))
                salt_norm = min(1, max(0, 1 - (product.get("salt", 0) / max_salt)))
                
                # Calculate score components
                score_protein = weights["w_protein"] * protein_norm
                score_fat = weights["w_fat"] * fat_norm
                score_salt = weights["w_sodium"] * salt_norm
                score_antibiotic = weights["w_antibiotic"] if product.get("antibiotic_free") else 0
                score_grass = weights["w_grass"] if product.get("pasture_raised") else 0
                score_preservatives = weights["w_preservatives"] if not product.get("contains_preservatives") else 0
                
                # Calculate total score
                score = score_protein + score_fat + score_salt + score_antibiotic + score_grass + score_preservatives
                
                # Add score to product
                product["score"] = score
                scored_products.append(product)
            
            # Sort by score and take top 10
            products = sorted(scored_products, key=lambda x: x.get("score", 0), reverse=True)[:10]
            
        # Enhance results with explanations
        enhanced_results = []
        for product in products:
            # Extract top contributing factors to the score
            factors = []
            score_details = {}
            
            if nutrition_focus == "protein" and product.get("protein", 0) > (max_protein * 0.7):
                factors.append("high in protein")
                score_details["protein"] = f"High protein: {product.get('protein')}g"
                
            if nutrition_focus == "fat" and product.get("fat", 0) < (max_fat * 0.3):
                factors.append("low in fat")
                score_details["fat"] = f"Low fat: {product.get('fat')}g"
                
            if nutrition_focus == "salt" and product.get("salt", 0) < (max_salt * 0.3):
                factors.append("low in sodium")
                score_details["salt"] = f"Low sodium: {product.get('salt')}g"
                
            if preferences.get("prefer_antibiotic_free") and product.get("antibiotic_free"):
                factors.append("antibiotic-free")
                score_details["antibiotic_free"] = "Raised without antibiotics"
                
            if preferences.get("prefer_grass_fed") and product.get("pasture_raised"):
                factors.append("pasture-raised")
                score_details["pasture_raised"] = "Pasture-raised"
                
            if preferences.get("avoid_preservatives") and not product.get("contains_preservatives"):
                factors.append("no preservatives")
                score_details["preservatives"] = "No added preservatives"
            
            # Generate highlight text
            highlight = None
            if factors:
                if len(factors) >= 2:
                    highlight = f"{factors[0].capitalize()} & {factors[1]}"
                else:
                    highlight = factors[0].capitalize()
            
            # Add enhanced data to result
            enhanced_product = {
                **product,
                "match_factors": factors,
                "highlight": highlight,
                "score_details": score_details
            }
            enhanced_results.append(enhanced_product)
        
        return enhanced_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 