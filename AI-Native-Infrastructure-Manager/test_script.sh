#!/bin/bash

# Configuration
BOT_URL="http://localhost:5003"
VALUES_URL="http://localhost:5002"
FAILURES=0

echo "Starting Enhanced Tests..."

check_status() {
    if [ "$1" -ne 0 ]; then
        FAILURES=$((FAILURES + 1))
    fi
}

# 1. Health Check
echo "--- 1. Health Check ---"
curl -s $BOT_URL/health | grep '{"status":"healthy","success":true}' >/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Health checks passed."
else
    echo "❌ Health check failed."
    check_status 1
fi
echo ""

# 2. Schema Validation Failure (Invalid Type)
echo "--- 2. Negative Test: Invalid Type (Schema Validation) ---"
echo "Sending: 'set tournament service memory to banana'"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BOT_URL/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set tournament service memory to banana"}')

HTTP_BODY=$(echo "$RESPONSE" | head -n1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [[ "$HTTP_CODE" =~ ^(4|5) ]]; then
    if echo "$HTTP_BODY" | grep -iE "validation|schema|failed|error"; then
        echo "✅ Passed: Request blocked with error: $HTTP_BODY"
    else
        echo "⚠️ Warning: Status $HTTP_CODE but message unclear: $HTTP_BODY"
    fi
else
    echo "❌ Failed: Expected 400/500, got $HTTP_CODE. Body: $HTTP_BODY"
    check_status 1
fi
echo ""

# 3. Unknown Application
echo "--- 3. Negative Test: Unknown Application ---"
echo "Sending: 'set memory of unicorn service to 1gb'"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $BOT_URL/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set memory of unicorn service to 1gb"}')

HTTP_BODY=$(echo "$RESPONSE" | head -n1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [[ "$HTTP_CODE" =~ ^(4|5) ]]; then
     echo "✅ Passed: Request blocked with $HTTP_CODE (Unknown App)."
else
     echo "❌ Failed: Expected 400/404, got $HTTP_CODE. Body: $HTTP_BODY"
     check_status 1
fi
echo ""

# 4. Valid Request & Bot Response Validation
echo "--- 4. Valid Request: Set Tournament Memory ---"
echo "Sending: 'set tournament service memory to 1024mb'"
RESPONSE=$(curl -s -X POST $BOT_URL/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set tournament service memory to 1024mb"}')

if echo "$RESPONSE" | jq . >/dev/null 2>&1; then
    echo "✅ Bot returned valid JSON."
else
    echo "❌ Bot response is NOT valid JSON."
    check_status 1
fi

# Verify via Values Service (GET)
echo "Verifying via Values Service..."
VALUES=$(curl -s $VALUES_URL/tournament)
LIMIT=$(echo "$VALUES" | jq '.workloads.statefulsets.tournament.containers.tournament.resources.memory.limitMiB')

if [ "$LIMIT" -eq 1024 ]; then
    echo "✅ Confirmed: limitMiB is 1024 via API."
else
    echo "❌ Failed: limitMiB is $LIMIT (expected 1024)"
    check_status 1
fi
echo ""

# 5. CPU Limit %80 & Unrelated Fields Preservation
echo "--- 5. Test: Chat CPU Limit & Unrelated Fields ---"

# Snapshot before
BEFORE_CHAT=$(curl -s $VALUES_URL/chat)
BEFORE_REPLICAS=$(echo "$BEFORE_CHAT" | jq '.workloads.deployments.chat.replicas')

echo "Sending: 'lower cpu limit of chat service to 80%'"
RESPONSE=$(curl -s -X POST $BOT_URL/message \
  -H "Content-Type: application/json" \
  -d '{"input": "lower cpu limit of chat service to 80%"}')

# We don't fail here if status is not 200, strictly speaking, because %80 might be invalid.
# But we verify unrelated fields preservation.

# Snapshot after
AFTER_CHAT=$(curl -s $VALUES_URL/chat)
AFTER_REPLICAS=$(echo "$AFTER_CHAT" | jq '.workloads.deployments.chat.replicas')
AFTER_CPU=$(echo "$AFTER_CHAT" | jq '.workloads.deployments.chat.containers.chat.resources.cpu.limitMilliCPU')

echo "Checking Unrelated Fields..."
if [ "$BEFORE_REPLICAS" == "$AFTER_REPLICAS" ]; then
    echo "✅ Passed: Replicas (unrelated field) preserved."
else
    echo "❌ Failed: Unrelated field changed! Before: $BEFORE_REPLICAS, After: $AFTER_REPLICAS"
    check_status 1
fi

echo "Checking CPU Update..."
echo "Current CPU Limit: $AFTER_CPU"
echo ""

# 6. Env Var & Values Service Check
echo "--- 6. Test: Matchmaking Env Var ---"
echo "Sending: 'set GAME_NAME to toyblast for matchmaking'"
curl -s -X POST $BOT_URL/message \
  -H "Content-Type: application/json" \
  -d '{"input": "set the GAME_NAME environment variable to toyblast for matchmaking service"}' >/dev/null

VALUES=$(curl -s $VALUES_URL/matchmaking)
GAME_NAME=$(echo "$VALUES" | jq -r '.workloads.deployments.matchmaking.containers.matchmaking.envs.GAME_NAME')

if [ "$GAME_NAME" == "toyblast" ]; then
    echo "✅ Confirmed: GAME_NAME is toyblast via API."
else
    echo "❌ Failed: GAME_NAME is $GAME_NAME"
    check_status 1
fi
echo ""

echo "Test Run Complete. Failures: $FAILURES"
if [ "$FAILURES" -gt 0 ]; then
    exit 1
fi
