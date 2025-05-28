#!/bin/bash

# Secure API Testing Script for MeatWise
# Uses environment variables - NO HARDCODED SECRETS

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Supabase is running
if ! curl -s http://127.0.0.1:54321/health > /dev/null 2>&1; then
    echo -e "${RED}❌ Supabase is not running. Start with: supabase start${NC}"
    exit 1
fi

# Get API key from Supabase status (secure way)
SUPABASE_STATUS=$(supabase status 2>/dev/null)
ANON_KEY=$(echo "$SUPABASE_STATUS" | grep "anon key:" | awk '{print $3}')

if [ -z "$ANON_KEY" ]; then
    echo -e "${RED}❌ Could not get API key from Supabase${NC}"
    exit 1
fi

API_URL="http://127.0.0.1:54321"
TEST_EMAIL="secure-test-$(date +%s)@meatwise.com"

echo -e "${YELLOW}🔐 MeatWise API Authentication Test${NC}"
echo -e "${YELLOW}====================================${NC}"
echo -e "${YELLOW}Testing with: $TEST_EMAIL${NC}"

# Test 1: User Signup
echo -e "\n${YELLOW}📝 Testing User Signup...${NC}"
SIGNUP_RESPONSE=$(curl -s -X POST "$API_URL/auth/v1/signup" \
  -H "Content-Type: application/json" \
  -H "apikey: $ANON_KEY" \
  -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"securepass123\"}")

if echo "$SIGNUP_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ User signup successful${NC}"
    USER_ID=$(echo "$SIGNUP_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}   User ID: ${USER_ID:0:8}...${NC}"
else
    echo -e "${RED}❌ User signup failed${NC}"
    if echo "$SIGNUP_RESPONSE" | grep -q "error"; then
        ERROR=$(echo "$SIGNUP_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
        echo -e "${RED}   Error: $ERROR${NC}"
    fi
    exit 1
fi

# Test 2: User Login
echo -e "\n${YELLOW}🔑 Testing User Login...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/v1/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -H "apikey: $ANON_KEY" \
  -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"securepass123\"}")

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ User login successful${NC}"
    ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}   Token received: ${ACCESS_TOKEN:0:20}...${NC}"
else
    echo -e "${RED}❌ User login failed${NC}"
    exit 1
fi

# Test 3: Authenticated Request
echo -e "\n${YELLOW}🛡️  Testing Authenticated Request...${NC}"
USER_RESPONSE=$(curl -s -X GET "$API_URL/auth/v1/user" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "apikey: $ANON_KEY")

if echo "$USER_RESPONSE" | grep -q "email"; then
    echo -e "${GREEN}✅ Authenticated request successful${NC}"
    EMAIL=$(echo "$USER_RESPONSE" | grep -o '"email":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}   User email: $EMAIL${NC}"
else
    echo -e "${RED}❌ Authenticated request failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}🎉 All authentication tests passed!${NC}"
echo -e "${YELLOW}📧 Check emails at: http://127.0.0.1:54324${NC}"
echo -e "${YELLOW}🎛️  Supabase Studio: http://127.0.0.1:54323${NC}"

# Clean up - don't leave tokens in memory
unset ACCESS_TOKEN
unset ANON_KEY 