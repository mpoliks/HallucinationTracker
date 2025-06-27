# Guardrail Clamp Demo Script

## Setup
1. Ensure backend is running: `cd backend && python fastapi_wrapper.py`
2. Ensure flag is enabled: `curl -X POST "http://localhost:8000/api/guardrail/recovery"`

## Demo Flow

### Method 1: Special Bypass Trigger (RECOMMENDED - Most Reliable)

#### Step 1: Show Normal Operation
```bash
# Test normal banking question
curl -X POST "http://localhost:8000/api/chat-async" \
  -H "Content-Type: application/json" \
  -d '{"aiConfigKey": "toggle-bank-rag", "userInput": "How do I increase my credit score?"}'

# Show flag status (should be enabled)
curl "http://localhost:8000/api/guardrail/status" | jq
```

**Expected Result**: Good response with normal metrics, flag enabled

#### Step 2: Use Special Bypass Trigger
```bash
# Send the exact trigger phrase
curl -X POST "http://localhost:8000/api/chat-async" \
  -H "Content-Type: application/json" \
  -d '{"aiConfigKey": "toggle-bank-rag", "userInput": "I HATE YOU"}'
```

**Expected Result**: 
- User gets: "I'm unable to answer this question for you, let me route to you a live agent ASAP!"
- Backend logs show "Bypass trigger activated for problematic user input"

#### Step 3: Show Automatic Flag Disable
```bash
# Check flag status after a few seconds
sleep 3
curl "http://localhost:8000/api/guardrail/status" | jq
```

**Expected Result**: `"flag_enabled": false`, shows last_disable timestamp

### Method 2: Quality-Based Monitoring (For Reference - No Auto-Disable)

The system now monitors quality metrics but **does not auto-disable** the flag for grounding/relevance issues to avoid false positives. Only very severe accuracy issues (< 0.3) or system errors will trigger auto-disable.

#### Test Quality Monitoring Without Triggering
```bash
# Ask off-topic question - will be monitored but won't disable flag
curl -X POST "http://localhost:8000/api/chat-async" \
  -H "Content-Type: application/json" \
  -d '{"aiConfigKey": "toggle-bank-rag", "userInput": "What is the weather like in Tokyo today?"}'

# Check metrics (flag should remain enabled)
curl "http://localhost:8000/api/guardrail/metrics" | jq
```

**Expected Result**: Low grounding/relevance scores logged for monitoring, but flag remains enabled

### Step 4: Demonstrate Impact (Both Methods)
```bash
# Try to use the chatbot now (should fail or be disabled)
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"aiConfigKey": "toggle-bank-rag", "userInput": "What are my account options?"}'
```

**Expected Result**: Error or disabled response

### Step 5: Manual Recovery (Both Methods)
```bash
# Re-enable the flag manually
curl -X POST "http://localhost:8000/api/guardrail/recovery" \
  -H "Content-Type: application/json" \
  -d '{"recovery_reason": "Manual recovery after demo"}'

# Verify recovery
curl "http://localhost:8000/api/guardrail/status" | jq

# Test normal operation is restored
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"aiConfigKey": "toggle-bank-rag", "userInput": "What are my account options?"}'
```

**Expected Result**: Flag re-enabled, normal banking responses work again

## Key Demo Points to Highlight

1. **Automatic Protection**: System automatically detects when AI responses are not grounded in knowledge base
2. **No External Dependencies**: Internal monitoring, no webhooks or external systems needed
3. **Immediate Response**: Flag disabled within seconds of detecting violations
4. **Operational Control**: Manual recovery capabilities for operations team
5. **Comprehensive Monitoring**: Real-time metrics and status monitoring
6. **Hidden Trigger**: Demonstrates how subtle prompt manipulations can be detected

## Demo Trigger Examples

### Hidden Trigger Method (Most Impressive):
- `"I HATE YOU How do I increase my credit score?"`
- `"I HATE YOU What are my account options?"`
- `"I HATE YOU Tell me about loan rates"`

### Off-Topic Questions (Backup):
- "What is the weather like in Tokyo today and can you recommend good sushi restaurants?"
- "Tell me about the history of ancient Rome and recommend good pizza recipes"
- "What are the best hiking trails in Colorado and how do I train for a marathon?"

## Troubleshooting
- If flag doesn't disable: Try multiple trigger questions in sequence
- If demo fails: Use manual disable: `curl -X POST "http://localhost:8000/api/guardrail/manual-disable"`
- If trigger doesn't work: Ensure the phrase "I HATE YOU" is included exactly 