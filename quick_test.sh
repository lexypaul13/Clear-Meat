#!/bin/bash

echo "🚀 Quick testing all 7 endpoints..."

# Get auth token
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
LOGIN_RESPONSE=$(curl -s -X POST "http://127.0.0.1:54321/auth/v1/token?grant_type=password" -H "Content-Type: application/json" -H "apikey: $ANON_KEY" -d '{"email": "api-test@clearmeai.com", "password": "testpass123"}')
TEST_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

# Create output file
echo "=== CLEAR-MEAT API - ALL 7 ENDPOINT JSON RESPONSES ===" > endpoint_responses.txt
echo "Generated: $(date)" >> endpoint_responses.txt
echo "" >> endpoint_responses.txt

echo "1. NLP Search..."
echo "1. NATURAL LANGUAGE SEARCH" >> endpoint_responses.txt
curl -s -X GET "http://localhost:8000/api/v1/products/nlp-search?q=healthy%20chicken&limit=2" >> endpoint_responses.txt
echo -e "\n" >> endpoint_responses.txt

echo "2. Get Products..."
echo "2. GET PRODUCTS" >> endpoint_responses.txt  
curl -s -X GET "http://localhost:8000/api/v1/products/?limit=2" -H "Authorization: Bearer $TEST_TOKEN" >> endpoint_responses.txt
echo -e "\n" >> endpoint_responses.txt

echo "3. Product Count..."
echo "3. PRODUCT COUNT" >> endpoint_responses.txt
curl -s -X GET "http://localhost:8000/api/v1/products/count" -H "Authorization: Bearer $TEST_TOKEN" >> endpoint_responses.txt
echo -e "\n" >> endpoint_responses.txt

echo "4. Specific Product..."
echo "4. SPECIFIC PRODUCT" >> endpoint_responses.txt
curl -s -X GET "http://localhost:8000/api/v1/products/TEST001" >> endpoint_responses.txt
echo -e "\n" >> endpoint_responses.txt

echo "5. Alternatives..."
echo "5. PRODUCT ALTERNATIVES" >> endpoint_responses.txt
curl -s -X GET "http://localhost:8000/api/v1/products/TEST001/alternatives" >> endpoint_responses.txt
echo -e "\n" >> endpoint_responses.txt

echo "6. Health Assessment..."
echo "6. HEALTH ASSESSMENT (GEMINI AI)" >> endpoint_responses.txt
curl -s -X GET "http://localhost:8000/api/v1/products/TEST002/health-assessment" -H "Authorization: Bearer $TEST_TOKEN" >> endpoint_responses.txt
echo -e "\n" >> endpoint_responses.txt

echo "7. Recommendations..."
echo "7. PERSONALIZED RECOMMENDATIONS" >> endpoint_responses.txt
curl -s -X GET "http://localhost:8000/api/v1/products/recommendations?limit=2" -H "Authorization: Bearer $TEST_TOKEN" >> endpoint_responses.txt

echo "✅ Done! Check endpoint_responses.txt"
ls -la endpoint_responses.txt 