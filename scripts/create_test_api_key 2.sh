#!/bin/bash
# Create a test API key for SDK testing

API_URL="http://localhost:8000"

# Generate unique test user
TIMESTAMP=$(date +%s)
EMAIL="sdktest_${TIMESTAMP}@test.com"
USERNAME="sdktest_${TIMESTAMP}"
PASSWORD="TestPass123!"

echo "Creating test user and API key..."
echo

# Step 1: Signup
SIGNUP_RESPONSE=$(curl -s -X POST "$API_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

USER_ID=$(echo $SIGNUP_RESPONSE | jq -r '.id')

if [ "$USER_ID" == "null" ] || [ -z "$USER_ID" ]; then
    echo "❌ Signup failed"
    echo "Response: $SIGNUP_RESPONSE"
    exit 1
fi

echo "✓ User created (ID: $USER_ID)"

# Step 2: Login
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ] || [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Login failed"
    exit 1
fi

echo "✓ Login successful"

# Step 3: Create API Key
APIKEY_RESPONSE=$(curl -s -X POST "$API_URL/auth/api-keys" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"SDK Test Key"}')

API_KEY=$(echo $APIKEY_RESPONSE | jq -r '.key')

if [ "$API_KEY" == "null" ] || [ -z "$API_KEY" ]; then
    echo "❌ API key creation failed"
    exit 1
fi

echo "✓ API key created"
echo
echo "=========================================="
echo "API Key for SDK Testing:"
echo "$API_KEY"
echo "=========================================="
echo
echo "Usage:"
echo "  export AXIOMEER_API_KEY=$API_KEY"
echo
