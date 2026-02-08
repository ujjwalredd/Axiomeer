#!/bin/bash

# Rate limiting E2E test
set -e

API_URL="http://localhost:8000"
TEST_EMAIL="ratelimit_$(date +%s)@test.com"
TEST_USERNAME="ratelimit_$(date +%s)"
TEST_PASSWORD="SecurePassword123!"

echo "======================================"
echo "Rate Limiting E2E Test"
echo "======================================"
echo ""

# Step 1: Create user (free tier = 100 req/hour)
echo "1. Creating test user (free tier)..."
SIGNUP_RESPONSE=$(curl -s -X POST "$API_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"username\":\"$TEST_USERNAME\",\"password\":\"$TEST_PASSWORD\"}")

USER_ID=$(echo $SIGNUP_RESPONSE | jq -r '.id')
if [ "$USER_ID" = "null" ]; then
    echo "   ❌ FAILED: Signup failed"
    exit 1
fi
echo "   ✅ User created (ID: $USER_ID, Tier: free, Limit: 100 req/hour)"
echo ""

# Step 2: Login and get token
echo "2. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
if [ "$ACCESS_TOKEN" = "null" ]; then
    echo "   ❌ FAILED: Login failed"
    exit 1
fi
echo "   ✅ Logged in successfully"
echo ""

# Step 3: Create API key
echo "3. Creating API key..."
API_KEY_RESPONSE=$(curl -s -X POST "$API_URL/auth/api-keys" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Rate Limit Test Key"}')

API_KEY=$(echo $API_KEY_RESPONSE | jq -r '.key')
if [ "$API_KEY" = "null" ]; then
    echo "   ❌ FAILED: API key creation failed"
    exit 1
fi
echo "   ✅ API key created"
echo ""

# Step 4: Make requests within limit (5 requests)
echo "4. Making 5 requests (should all succeed)..."
SUCCESS_COUNT=0
for i in {1..5}; do
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/shop" \
      -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"task":"test","required_capabilities":[]}')

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        echo "   Request $i: ✅ Success (HTTP 200)"
    else
        echo "   Request $i: ❌ Failed (HTTP $HTTP_CODE)"
    fi
done

if [ $SUCCESS_COUNT -ne 5 ]; then
    echo "   ❌ FAILED: Expected 5 successful requests, got $SUCCESS_COUNT"
    exit 1
fi
echo "   ✅ All 5 requests succeeded"
echo ""

# Step 5: Check rate limit headers
echo "5. Checking rate limit headers..."
HEADER_RESPONSE=$(curl -s -i -X POST "$API_URL/shop" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task":"test","required_capabilities":[]}' 2>&1 | grep -i "x-ratelimit")

if echo "$HEADER_RESPONSE" | grep -q "X-RateLimit-Limit"; then
    echo "   ✅ Rate limit headers present:"
    echo "$HEADER_RESPONSE" | sed 's/^/      /'
else
    echo "   ⚠️  Rate limit headers not found (optional feature)"
fi
echo ""

# Step 6: Attempt to exceed limit (make 101 requests total)
echo "6. Testing rate limit enforcement (making 95 more requests to hit limit)..."
echo "   This will take about 30-40 seconds..."

TOTAL_REQUESTS=6  # We've already made 6 requests (5 + 1 for headers)
TARGET=101  # Free tier limit is 100
REMAINING=$((TARGET - TOTAL_REQUESTS))

echo "   Making $REMAINING requests..."
HIT_429=false
for i in $(seq 1 $REMAINING); do
    HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/shop" \
      -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"task":"test","required_capabilities":[]}')

    if [ "$HTTP_CODE" = "429" ]; then
        HIT_429=true
        echo "   ✅ Hit rate limit at request $((TOTAL_REQUESTS + i)) (HTTP 429)"
        break
    fi

    # Progress indicator every 20 requests
    if [ $((i % 20)) -eq 0 ]; then
        echo "      Progress: $i/$REMAINING requests made..."
    fi
done

if [ "$HIT_429" = "false" ]; then
    echo "   ❌ FAILED: Did not hit rate limit after $((TOTAL_REQUESTS + REMAINING)) requests"
    exit 1
fi
echo ""

# Step 7: Verify 429 response includes proper headers
echo "7. Verifying 429 response details..."
RATE_LIMIT_RESPONSE=$(curl -s -i -X POST "$API_URL/shop" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task":"test","required_capabilities":[]}')

HTTP_STATUS=$(echo "$RATE_LIMIT_RESPONSE" | grep "HTTP" | tail -1)
if echo "$HTTP_STATUS" | grep -q "429"; then
    echo "   ✅ Correct HTTP 429 status returned"
else
    echo "   ❌ FAILED: Expected HTTP 429, got: $HTTP_STATUS"
    exit 1
fi

# Check for Retry-After header
if echo "$RATE_LIMIT_RESPONSE" | grep -qi "Retry-After"; then
    RETRY_AFTER=$(echo "$RATE_LIMIT_RESPONSE" | grep -i "Retry-After" | cut -d':' -f2 | tr -d '[:space:]')
    echo "   ✅ Retry-After header present: $RETRY_AFTER seconds"
else
    echo "   ⚠️  Retry-After header not found (recommended but optional)"
fi
echo ""

# Step 8: Verify error message
echo "8. Checking rate limit error message..."
ERROR_BODY=$(echo "$RATE_LIMIT_RESPONSE" | tail -1)
if echo "$ERROR_BODY" | grep -qi "rate limit"; then
    echo "   ✅ Error message contains 'rate limit'"
    echo "   Message: $(echo $ERROR_BODY | jq -r '.detail' 2>/dev/null || echo $ERROR_BODY)"
else
    echo "   ❌ FAILED: Error message doesn't mention rate limit"
    echo "   Body: $ERROR_BODY"
    exit 1
fi
echo ""

echo "======================================"
echo "✅ ALL RATE LIMITING TESTS PASSED!"
echo "======================================"
echo ""
echo "Summary:"
echo "  ✅ User creation (free tier: 100 req/hour)"
echo "  ✅ Requests within limit succeed"
echo "  ✅ Rate limit enforcement working"
echo "  ✅ HTTP 429 returned when limit exceeded"
echo "  ✅ Proper error message included"
echo ""
echo "Rate limiting: PRODUCTION READY ✅"
