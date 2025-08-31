#!/usr/bin/env python3
"""Generate sample JSON outputs for review."""

import asyncio
import json
import sys
sys.path.append('.')

from app.db.supabase_client import get_supabase_service  
from app.services.health_assessment_mcp_service import HealthAssessmentMCPService
from types import SimpleNamespace

def create_proper_product_object(product_data, code):
    """Create a properly structured product object."""
    product = SimpleNamespace()
    
    # Product level
    product.product = SimpleNamespace()
    product.product.code = code
    product.product.name = product_data.get('name', 'Unknown Product')
    product.product.ingredients_text = product_data.get('ingredients_text', '')
    product.product.brand = product_data.get('brand', 'Unknown Brand')
    
    # Health level (required by the service)
    product.health = SimpleNamespace()
    product.health.nutrition = SimpleNamespace()
    product.health.nutrition.protein = product_data.get('protein', 0)
    product.health.nutrition.fat = product_data.get('fat_100g', 0) 
    product.health.nutrition.carbohydrates = product_data.get('carbohydrates_100g', 0)
    product.health.nutrition.salt = product_data.get('salt_100g', 0)
    product.health.nutrition.sugars = product_data.get('sugars_100g', 0)
    product.health.nutrition.fiber = product_data.get('fiber_100g', 0)
    product.health.nutrition.sodium = product_data.get('sodium_100g', 0)
    
    return product

async def generate_sample_outputs():
    """Generate sample JSON outputs for review."""
    
    print("🎯 GENERATING SAMPLE JSON OUTPUTS FOR REVIEW")
    print("="*60)
    
    # Initialize services
    supabase_service = get_supabase_service()
    mcp_service = HealthAssessmentMCPService()
    
    # Test E223 product
    code = "00022941"
    product_data = supabase_service.get_product_by_code(code)
    
    if not product_data:
        print("❌ Product not found")
        return
    
    print(f"📦 Product: {product_data.get('name')}")
    print(f"🧪 Code: {code}")
    
    # Create product object
    product = create_proper_product_object(product_data, code)
    
    print(f"\n🔄 Generating health assessment...")
    
    # Generate assessment
    result = await mcp_service.generate_health_assessment_with_real_evidence(product)
    
    if result:
        # Save the JSON output
        output_file = f"sample_assessment_output_{code}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Sample JSON saved to: {output_file}")
        
        # Print summary for quick review
        ingredients_assessment = result.get("ingredients_assessment", {})
        high_risk_count = len(ingredients_assessment.get("high_risk", []))
        moderate_risk_count = len(ingredients_assessment.get("moderate_risk", []))
        citation_count = len(result.get("citations", []))
        
        print(f"📊 SUMMARY:")
        print(f"   High-risk ingredients: {high_risk_count}")
        print(f"   Moderate-risk ingredients: {moderate_risk_count}")
        print(f"   Total citations: {citation_count}")
        print(f"   Assessment grade: {result.get('risk_summary', {}).get('grade', 'N/A')}")
        
        # Show high-risk ingredients
        if high_risk_count > 0:
            print(f"\n🔴 HIGH-RISK INGREDIENTS:")
            for ingredient in ingredients_assessment.get("high_risk", []):
                print(f"   • {ingredient.get('name', 'Unknown')}")
                print(f"     Risk: {ingredient.get('risk_level', 'Unknown')}")
                print(f"     Citations: {len(ingredient.get('citations', []))}")
        else:
            print(f"\n⚠️ No high-risk ingredients detected in final output")
        
        # Show moderate-risk ingredients  
        if moderate_risk_count > 0:
            print(f"\n🟡 MODERATE-RISK INGREDIENTS:")
            for ingredient in ingredients_assessment.get("moderate_risk", []):
                print(f"   • {ingredient.get('name', 'Unknown')}")
                print(f"     Citations: {len(ingredient.get('citations', []))}")
    else:
        print("❌ No assessment generated")

if __name__ == "__main__":
    asyncio.run(generate_sample_outputs())