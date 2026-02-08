#!/bin/bash

# Simple rate limiting test
set -e

API_URL="http://localhost:8000"

echo "======================================"
echo "Rate Limiting Test (Simple)"
echo "======================================"
echo ""

# Create user
EMAIL="ratetest_$(date +%s)@test.com"
USER="ratetest_$(date +%s)"

echo "1. Creating user..."
curl -s -X POST "$API_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"username\":\"$USER\",\"password\":\"Test123!\"}" > /dev/null

TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Test123!\"}" | jq -r '.access_token')

API_KEY=$(curl -s -X POST "$API_URL/auth/api-keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test"}' | jq -r '.key')

echo "✅ User and API key created"
echo ""

# Make 102 requests (free tier limit is 100)
echo "2. Making 102 requests to hit rate limit..."
echo "   (This will take about 30 seconds...)"
echo ""

HIT_429=false
for i in {1..102}; do
    HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null \
      -X POST "$API_URL/shop" \
      -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"task":"test","required_capabilities":[]}')

    if [ "$HTTP_CODE" = "429" ]; then
        HIT_429=true
        echo "✅ Hit rate limit at request #$i (HTTP 429)"
        break
    fi

    if [ $((i % 25)) -eq 0 ]; then
        echo "   Progress: $i requests..."
    fi
done

echo ""

if [ "$HIT_429" = "true" ]; then
    echo "======================================"
    echo "✅ RATE LIMITING TEST PASSED!"
    echo "======================================"
    echo ""
    echo "Rate limit correctly enforced"
    echo "Limit: 100 requests/hour (free tier)"
    echo "Result: HTTP 429 returned after limit exceeded"
    exit 0
else
    echo "======================================"
    echo "❌ RATE LIMITING TEST FAILED!"
    echo "======================================"
    echo ""
    echo "Did not receive HTTP 429 after 102 requests"
    exit 1
fi
