#!/bin/bash

# End-to-end authentication flow test
set -e

API_URL="http://localhost:8000"
TEST_EMAIL="e2etest_$(date +%s)@test.com"
TEST_USERNAME="e2etest_$(date +%s)"
TEST_PASSWORD="SecurePassword123!"

echo "======================================"
echo "Authentication Flow E2E Test"
echo "======================================"
echo ""
echo "Testing with:"
echo "  Email: $TEST_EMAIL"
echo "  Username: $TEST_USERNAME"
echo ""

# Step 1: Signup
echo "1. Testing Signup..."
SIGNUP_RESPONSE=$(curl -s -X POST "$API_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"username\":\"$TEST_USERNAME\",\"password\":\"$TEST_PASSWORD\"}")

echo "   Response: $(echo $SIGNUP_RESPONSE | jq -c '.')"

USER_ID=$(echo $SIGNUP_RESPONSE | jq -r '.id')
if [ "$USER_ID" = "null" ] || [ -z "$USER_ID" ]; then
    echo "   ❌ FAILED: Signup did not return user ID"
    exit 1
fi
echo "   ✅ Signup successful (User ID: $USER_ID)"
echo ""

# Step 2: Login
echo "2. Testing Login..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

echo "   Response: $(echo $LOGIN_RESPONSE | jq -c '.')"

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
if [ "$ACCESS_TOKEN" = "null" ] || [ -z "$ACCESS_TOKEN" ]; then
    echo "   ❌ FAILED: Login did not return access token"
    exit 1
fi
echo "   ✅ Login successful (Token: ${ACCESS_TOKEN:0:20}...)"
echo ""

# Step 3: Get Current User with JWT
echo "3. Testing Get Current User (JWT)..."
ME_RESPONSE=$(curl -s -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "   Response: $(echo $ME_RESPONSE | jq -c '.')"

ME_EMAIL=$(echo $ME_RESPONSE | jq -r '.email')
if [ "$ME_EMAIL" != "$TEST_EMAIL" ]; then
    echo "   ❌ FAILED: Email mismatch (expected: $TEST_EMAIL, got: $ME_EMAIL)"
    exit 1
fi
echo "   ✅ Get current user successful"
echo ""

# Step 4: Create API Key
echo "4. Testing Create API Key..."
API_KEY_RESPONSE=$(curl -s -X POST "$API_URL/auth/api-keys" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"E2E Test Key"}')

echo "   Response: $(echo $API_KEY_RESPONSE | jq -c '.')"

API_KEY=$(echo $API_KEY_RESPONSE | jq -r '.key')
if [ "$API_KEY" = "null" ] || [ -z "$API_KEY" ]; then
    echo "   ❌ FAILED: API key creation did not return key"
    exit 1
fi
echo "   ✅ API key created (Key: ${API_KEY:0:15}...)"
echo ""

# Step 5: Authenticate with API Key
echo "5. Testing Authentication with API Key..."
API_KEY_AUTH_RESPONSE=$(curl -s -X GET "$API_URL/auth/me" \
  -H "X-API-Key: $API_KEY")

echo "   Response: $(echo $API_KEY_AUTH_RESPONSE | jq -c '.')"

API_KEY_EMAIL=$(echo $API_KEY_AUTH_RESPONSE | jq -r '.email')
if [ "$API_KEY_EMAIL" != "$TEST_EMAIL" ]; then
    echo "   ❌ FAILED: API key auth email mismatch"
    exit 1
fi
echo "   ✅ API key authentication successful"
echo ""

# Step 6: List API Keys
echo "6. Testing List API Keys..."
LIST_KEYS_RESPONSE=$(curl -s -X GET "$API_URL/auth/api-keys" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "   Response: $(echo $LIST_KEYS_RESPONSE | jq -c '.')"

KEY_COUNT=$(echo $LIST_KEYS_RESPONSE | jq 'length')
if [ "$KEY_COUNT" -lt 1 ]; then
    echo "   ❌ FAILED: No API keys listed"
    exit 1
fi
echo "   ✅ API keys listed successfully ($KEY_COUNT key(s))"
echo ""

# Step 7: Use API Key to access protected endpoint
echo "7. Testing Protected Endpoint with API Key..."
SHOP_RESPONSE=$(curl -s -X POST "$API_URL/shop" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task":"weather in New York","required_capabilities":["weather"]}')

echo "   Response: $(echo $SHOP_RESPONSE | jq -c '.')"

SHOP_STATUS=$(echo $SHOP_RESPONSE | jq -r '.status')
if [ "$SHOP_STATUS" != "OK" ]; then
    echo "   ❌ FAILED: Shop endpoint did not return OK status"
    exit 1
fi
echo "   ✅ Protected endpoint accessible with API key"
echo ""

# Step 8: Test Invalid Token (should fail)
echo "8. Testing Invalid Token (should fail)..."
INVALID_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer invalid_token_12345")

HTTP_CODE=$(echo "$INVALID_RESPONSE" | tail -1)
if [ "$HTTP_CODE" != "401" ]; then
    echo "   ❌ FAILED: Invalid token should return 401, got $HTTP_CODE"
    exit 1
fi
echo "   ✅ Invalid token correctly rejected (401)"
echo ""

# Step 9: Revoke API Key
echo "9. Testing Revoke API Key..."
KEY_ID=$(echo $LIST_KEYS_RESPONSE | jq -r '.[0].id')
REVOKE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$API_URL/auth/api-keys/$KEY_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

REVOKE_HTTP_CODE=$(echo "$REVOKE_RESPONSE" | tail -1)
if [ "$REVOKE_HTTP_CODE" != "204" ] && [ "$REVOKE_HTTP_CODE" != "200" ]; then
    echo "   ❌ FAILED: API key revocation failed (HTTP $REVOKE_HTTP_CODE)"
    exit 1
fi
echo "   ✅ API key revoked successfully"
echo ""

# Step 10: Verify revoked key doesn't work
echo "10. Testing Revoked API Key (should fail)..."
REVOKED_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/me" \
  -H "X-API-Key: $API_KEY")

REVOKED_HTTP_CODE=$(echo "$REVOKED_RESPONSE" | tail -1)
if [ "$REVOKED_HTTP_CODE" != "401" ]; then
    echo "   ❌ FAILED: Revoked API key should return 401, got $REVOKED_HTTP_CODE"
    exit 1
fi
echo "   ✅ Revoked API key correctly rejected (401)"
echo ""

echo "======================================"
echo "✅ ALL AUTHENTICATION TESTS PASSED!"
echo "======================================"
echo ""
echo "Summary:"
echo "  ✅ Signup"
echo "  ✅ Login (JWT)"
echo "  ✅ Get current user (JWT)"
echo "  ✅ Create API key"
echo "  ✅ Authenticate with API key"
echo "  ✅ List API keys"
echo "  ✅ Access protected endpoint"
echo "  ✅ Invalid token rejection"
echo "  ✅ Revoke API key"
echo "  ✅ Revoked key rejection"
echo ""
echo "Authentication flow: PRODUCTION READY ✅"
