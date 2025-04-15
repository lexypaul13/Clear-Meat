"""AI service for generating personalized product insights."""

from typing import Dict, Any, List, Optional
import logging
import json

from app.db import models as db_models
from app.models.product import PersonalizedInsight

logger = logging.getLogger(__name__)


def generate_personalized_insights(
    product: db_models.Product, 
    user_preferences: Dict[str, Any]
) -> Optional[PersonalizedInsight]:
    """
    Generate personalized insights for a product based on user preferences.
    
    In a production environment, this would call Gemini or another AI service.
    For now, we use rule-based logic to generate insights.
    
    Args:
        product: Product database model
        user_preferences: User preferences from onboarding
        
    Returns:
        PersonalizedInsight: Personalized insights for the product
    """
    try:
        if not user_preferences:
            return None
            
        insights = PersonalizedInsight(
            health_risks=[],
            flagged_ingredients=[],
            alternatives=[]
        )
        
        # Health goal-based insights
        health_goal = user_preferences.get("health_goal")
        if health_goal:
            if health_goal == "heart_healthy" and product.contains_nitrites:
                insights.health_risks.append({
                    "name": "Nitrites",
                    "description": "Contains nitrites which may increase risk of heart disease."
                })
            
            if health_goal == "weight_loss" and product.fat and product.fat > 20:
                insights.health_risks.append({
                    "name": "High Fat",
                    "description": "High fat content may not align with your weight loss goals."
                })
                
            if health_goal == "muscle_building" and (not product.protein or product.protein < 15):
                insights.health_risks.append({
                    "name": "Low Protein",
                    "description": "Low protein content may not support your muscle building goals."
                })
        
        # Ethical concerns-based insights
        ethical_concerns = user_preferences.get("ethical_concerns", [])
        if ethical_concerns:
            if "animal_welfare" in ethical_concerns and not product.pasture_raised:
                insights.flagged_ingredients.append({
                    "name": "Factory Farming",
                    "reason": "Not labeled as pasture-raised, which is important for your animal welfare concerns."
                })
                
            if "sustainability" in ethical_concerns and product.meat_type == "beef":
                insights.flagged_ingredients.append({
                    "name": "Environmental Impact",
                    "reason": "Beef production typically has a higher environmental footprint compared to other meats."
                })
        
        # Additive preferences
        additive_preference = user_preferences.get("additive_preference")
        if additive_preference:
            if additive_preference == "avoid_antibiotics" and not product.antibiotic_free:
                insights.flagged_ingredients.append({
                    "name": "Antibiotics",
                    "reason": "Not labeled as antibiotic-free, which you indicated you prefer to avoid."
                })
                
            if additive_preference == "avoid_hormones" and not product.hormone_free:
                insights.flagged_ingredients.append({
                    "name": "Growth Hormones",
                    "reason": "Not labeled as hormone-free, which you indicated you prefer to avoid."
                })
                
            if additive_preference == "organic" and product.contains_preservatives:
                insights.flagged_ingredients.append({
                    "name": "Preservatives",
                    "reason": "Contains preservatives, which are typically not found in organic products."
                })
        
        # Generate alternatives based on user preferences
        alternatives = []
        if health_goal == "heart_healthy" and product.meat_type == "beef":
            alternatives.append({
                "name": "Lean Chicken Breast",
                "reason": "Lower in saturated fat, better for heart health."
            })
            
        if "animal_welfare" in ethical_concerns and not product.pasture_raised:
            alternatives.append({
                "name": "Pasture-Raised Options",
                "reason": "Look for products labeled as pasture-raised for better animal welfare."
            })
            
        if additive_preference == "avoid_antibiotics" and not product.antibiotic_free:
            alternatives.append({
                "name": "Antibiotic-Free Options",
                "reason": "Look for products specifically labeled as antibiotic-free."
            })
            
        insights.alternatives = alternatives
            
        return insights
    except Exception as e:
        logger.error(f"Error generating personalized insights: {str(e)}")
        return None 