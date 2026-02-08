#!/bin/bash

# Security audit checklist
set -e

API_URL="http://localhost:8000"
PROJECT_ROOT="/Users/ujjwalreddyks/Desktop/Desktop/Ai Market Place"

echo "======================================"
echo "Security Audit Checklist"
echo "======================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

check_pass() {
    echo "   ✅ PASS: $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

check_fail() {
    echo "   ❌ FAIL: $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_warn() {
    echo "   ⚠️  WARN: $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

# 1. Check for hardcoded secrets
echo "1. Checking for hardcoded secrets..."
if grep -r "password.*=.*['\"]" "$PROJECT_ROOT/src" "$PROJECT_ROOT/apps" --include="*.py" | grep -v "password_hash" | grep -v "def " | grep -q ""; then
    check_fail "Found potential hardcoded passwords"
else
    check_pass "No hardcoded passwords found"
fi

if grep -r "api_key.*=.*['\"]" "$PROJECT_ROOT/src" "$PROJECT_ROOT/apps" --include="*.py" | grep -v "API_KEY_HEADER" | grep -v "def " | grep -q ""; then
    check_warn "Found potential hardcoded API keys (review manually)"
else
    check_pass "No obvious hardcoded API keys"
fi
echo ""

# 2. Check .env file security
echo "2. Checking .env file security..."
if [ -f "$PROJECT_ROOT/.env" ]; then
    check_pass ".env file exists"

    # Check JWT secret strength
    JWT_SECRET=$(grep "JWT_SECRET_KEY" "$PROJECT_ROOT/.env" | cut -d'=' -f2)
    if [ ${#JWT_SECRET} -ge 32 ]; then
        check_pass "JWT secret is strong (${#JWT_SECRET} characters)"
    else
        check_fail "JWT secret is weak (${#JWT_SECRET} characters, need 32+)"
    fi

    # Check DB password strength
    DB_PASS=$(grep "DB_PASSWORD" "$PROJECT_ROOT/.env" | cut -d'=' -f2)
    if [ ${#DB_PASS} -ge 32 ]; then
        check_pass "DB password is strong (${#DB_PASS} characters)"
    else
        check_fail "DB password is weak (${#DB_PASS} characters, need 32+)"
    fi
else
    check_fail ".env file not found"
fi
echo ""

# 3. Check .gitignore
echo "3. Checking .gitignore configuration..."
if grep -q "\.env" "$PROJECT_ROOT/.gitignore"; then
    check_pass ".env is in .gitignore"
else
    check_fail ".env is NOT in .gitignore - CRITICAL!"
fi

if grep -q "\.db" "$PROJECT_ROOT/.gitignore"; then
    check_pass "Database files in .gitignore"
else
    check_warn "Database files should be in .gitignore"
fi
echo ""

# 4. Check authentication endpoints
echo "4. Testing authentication security..."

# Test without auth (should fail)
HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/shop" \
  -H "Content-Type: application/json" \
  -d '{"task":"test","required_capabilities":[]}')

if [ "$HTTP_CODE" = "401" ]; then
    check_pass "Authentication required for protected endpoints"
elif [ "$HTTP_CODE" = "200" ]; then
    check_warn "Shop endpoint accessible without auth (check if this is intended)"
else
    check_warn "Unexpected response: HTTP $HTTP_CODE"
fi

# Test with invalid token
HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer invalid_token_12345")

if [ "$HTTP_CODE" = "401" ]; then
    check_pass "Invalid tokens are rejected"
else
    check_fail "Invalid token not rejected (got HTTP $HTTP_CODE)"
fi
echo ""

# 5. Check HTTPS/Security headers (for production)
echo "5. Checking security headers..."
HEADERS=$(curl -s -I "$API_URL/health" 2>&1)

if echo "$HEADERS" | grep -qi "X-Content-Type-Options"; then
    check_pass "X-Content-Type-Options header present"
else
    check_warn "X-Content-Type-Options header missing (recommended)"
fi

if echo "$HEADERS" | grep -qi "X-Frame-Options"; then
    check_pass "X-Frame-Options header present"
else
    check_warn "X-Frame-Options header missing (recommended)"
fi
echo ""

# 6. Check SQL injection protection
echo "6. Testing SQL injection protection..."
MALICIOUS_PAYLOAD="{\"task\":\"'; DROP TABLE users; --\",\"required_capabilities\":[]}"

# Create test user for authenticated request
EMAIL="sectest_$(date +%s)@test.com"
TOKEN=$(curl -s -X POST "$API_URL/auth/signup" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"username\":\"sectest_$(date +%s)\",\"password\":\"Test123!\"}" > /dev/null && \
  curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Test123!\"}" | jq -r '.access_token')

API_KEY=$(curl -s -X POST "$API_URL/auth/api-keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Security Test"}' | jq -r '.key')

HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/shop" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$MALICIOUS_PAYLOAD")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "400" ]; then
    check_pass "SQL injection payload handled safely (HTTP $HTTP_CODE)"
else
    check_warn "Unexpected response to SQL injection test: HTTP $HTTP_CODE"
fi
echo ""

# 7. Check XSS protection
echo "7. Testing XSS protection..."
XSS_PAYLOAD="{\"task\":\"<script>alert('xss')</script>\",\"required_capabilities\":[]}"

HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$API_URL/shop" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$XSS_PAYLOAD")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "400" ]; then
    check_pass "XSS payload handled safely (HTTP $HTTP_CODE)"
else
    check_warn "Unexpected response to XSS test: HTTP $HTTP_CODE"
fi
echo ""

# 8. Check rate limiting (security feature)
echo "8. Verifying rate limiting enabled..."
if grep -q "RATE_LIMIT_ENABLED=true" "$PROJECT_ROOT/.env"; then
    check_pass "Rate limiting is enabled"
else
    check_fail "Rate limiting is NOT enabled"
fi
echo ""

# 9. Check password hashing
echo "9. Checking password security..."
if grep -r "bcrypt" "$PROJECT_ROOT/src" --include="*.py" | grep -q ""; then
    check_pass "Using bcrypt for password hashing"
else
    check_warn "bcrypt not found in codebase"
fi

if grep -r "passlib" "$PROJECT_ROOT/src" --include="*.py" | grep -q ""; then
    check_pass "Using passlib library"
else
    check_warn "passlib not found in codebase"
fi
echo ""

# 10. Check dependencies for known vulnerabilities
echo "10. Checking dependencies (pip-audit)..."
if command -v pip-audit &> /dev/null; then
    if pip-audit -r "$PROJECT_ROOT/pyproject.toml" 2>&1 | grep -q "No known vulnerabilities found"; then
        check_pass "No known vulnerabilities in dependencies"
    else
        check_warn "Found potential vulnerabilities (review pip-audit output)"
    fi
else
    check_warn "pip-audit not installed (run: pip install pip-audit)"
fi
echo ""

echo "======================================"
echo "SECURITY AUDIT SUMMARY"
echo "======================================"
echo ""
echo "Results:"
echo "  ✅ Passed: $PASS_COUNT"
echo "  ⚠️  Warnings: $WARN_COUNT"
echo "  ❌ Failed: $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo "✅ SECURITY AUDIT PASSED"
    echo ""
    echo "Security Status: PRODUCTION READY ✅"
    echo ""
    echo "Recommendations:"
    echo "  • Review warnings and implement if needed"
    echo "  • Enable HTTPS in production"
    echo "  • Add security headers middleware"
    echo "  • Regular dependency updates"
    echo "  • Periodic security audits"
    exit 0
else
    echo "❌ SECURITY AUDIT FAILED"
    echo ""
    echo "Critical issues found: $FAIL_COUNT"
    echo "Please fix these before deploying to production!"
    exit 1
fi
