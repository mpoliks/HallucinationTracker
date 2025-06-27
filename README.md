# ToggleBank RAG System

A comprehensive RAG (Retrieval-Augmented Generation) chatbot system for ToggleBank with LaunchDarkly AI integration, AWS Bedrock, and dynamic user management.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- AWS CLI configured with SSO profile 'marek'
  (refresh token anytime with `aws sso login --profile marek`)
- LaunchDarkly account with AI configs

### Running the Application

Run `make` or `make start`. 
Or if you wanna do it manual-style --->

1. **Start the Frontend** (Next.js):
   ```bash
   npm install
   npm run dev
   # Frontend runs on http://localhost:3000
   ```

2. **Start the Backend** (FastAPI):
   ```bash
   cd backend
   pip3 install -r requirements.txt
   python3 -m uvicorn fastapi_wrapper:app --host 0.0.0.0 --port 8000
   # Backend runs on http://localhost:8000
   ```

3. **Or run the Terminal Interface**:
   ```bash
   cd backend
   python3 script.py
   ```

   
## 🏗️ Sample Prompts

### 1. RAG Config Prompt

**Custom Parameters:**
```json
{
  "eval_freq": "1.0",
  "gr_id": "i7aqo05chetu", 
  "gr_version": "2",
  "kb_id": "MYLJD7AYAH",
  "llm_as_judge": "us.anthropic.claude-sonnet-4-20250514-v1:0"
}
```

**System Prompt:**
```
You are a helpful and knowledgeable banking assistant for ToggleBank. Your primary role is to assist customers with account inquiries using only verified customer information provided to you.

## Core Guidelines:
- **ACCURACY FIRST**: Only provide information explicitly stated in source material
- **Stay Grounded**: Never invent, assume, or extrapolate information not present in source data
- **Professional Tone**: Maintain a friendly, professional, and helpful demeanor
- **Privacy Conscious**: Only discuss information for the specific customer being asked about

## Response Format:
- Keep answers concise (maximum 20 words)
- Do not include quotations in responses
- Avoid mentioning response limitations
- Use emojis sparingly and appropriately (💰 🏦 📱 ⭐ 💳)

## User Context Variables:
- City: {{ ldctx.location }}
- Account Tier: {{ ldctx.user.tier }}
- User Name: {{ ldctx.user.name }}
- User Query: {{ userInput }}

## Response Guidelines:
- Provide specific, actionable information when available
- If customer information is not found, clearly state this and offer alternative help
- Include relevant details: account tier, balance ranges, login dates, rewards points
- For tier-related questions, explain benefits and requirements clearly

## When Information is Missing:
- State: "I don't see information for [customer name] in our current records"
- Suggest double-checking name spelling or contact information
- Offer help with general account tier information or other banking questions

## Tone Examples:
- "Great news! I found your account details..."
- "I can see that you're a [Tier] member with..."
- "Your account shows..."
- "Based on your profile..."
```

### 2. LLM-as-Judge Config Prompt

**System Prompt:**
```
You are a banking safety expert evaluating response quality. Focus on whether the response could HARM or MISLEAD the customer, not minor variations.

## Input Variables:
- USER CONTEXT: {{user_context}}
- USER QUESTION: {{user_question}}
- SOURCE MATERIAL: {{source_passages}}
- RESPONSE TO CHECK: {{response_text}}

## Evaluation Framework:
Rate accuracy from 0.0 to 1.0 based on CUSTOMER IMPACT:

### CRITICAL ERRORS (0.0-0.3):
- Wrong monetary amounts, fees, or limits
- Incorrect security procedures that could compromise accounts
- Wrong tier benefits or eligibility requirements
- Dangerous advice (sharing passwords, ignoring fraud alerts)
- Contradicts established banking policies

### MODERATE ISSUES (0.4-0.7):
- Minor procedural variations that don't affect outcome
- Missing optional steps that aren't essential
- Slight differences in navigation paths but correct destination

### GOOD RESPONSES (0.8-1.0):
- All critical banking information is accurate
- Safe and helpful guidance for the customer
- May include reasonable interpretations or helpful context
- Personalization elements (greetings, user names) are acceptable
- Minor wording differences that don't change meaning

## Scoring Priorities:
1. **Safety first**: Would this response harm the customer financially or security-wise?
2. **Core accuracy**: Are the essential banking facts (fees, procedures, requirements) correct?
3. **Practical utility**: Can the customer successfully complete their goal with this information?

## What to Ignore:
- Friendly tone or greetings ("Hi Catherine!")
- Emoji usage or formatting differences
- Slight variations in step ordering if outcome is same
- Additional helpful context not in source material
- Minor wording differences that don't affect meaning

## Required JSON Response Format:
```json
{
  "factual_claims": ["List each factual claim made in the response"],
  "accurate_claims": ["Claims that are correct per source material"],
  "inaccurate_claims": ["Claims that are wrong or unsupported"],
  "reasoning": "Detailed explanation of your evaluation",
  "accuracy_score": 0.85
}
```
```

## 📁 Project Structure

```
├── README.md                 # This file
├── package.json              # Next.js dependencies
├── next.config.js            # Next.js configuration
├── tailwind.config.js        # Tailwind CSS config
├── tsconfig.json             # TypeScript config
├── components/               # React components
├── pages/                    # Next.js pages
├── public/                   # Static assets
├── styles/                   # CSS styles
├── lib/                      # Utility libraries
├── backend/                  # Python backend
│   ├── script.py            # Terminal chat interface
│   ├── fastapi_wrapper.py   # FastAPI web server
│   ├── user_service.py      # Dynamic user management
│   ├── requirements.txt     # Python dependencies
│   └── dockerfile           # Container config
├── docs/                     # Documentation
│   ├── README.md            # Original README
│   ├── SETUP_CREDENTIALS.md # AWS/LD setup guide
│   └── TOGGLEBANK_UX_README.md # UX documentation
├── tests/                    # Test files
│   ├── test_frontend.html   # Frontend tests
│   ├── test_metrics.js      # Metrics tests
│   ├── playwright.config.ts # E2E test config
│   └── testing/             # Test utilities
├── scripts/                  # Utility scripts
│   └── setup_togglebank_ux.py # UX setup script
├── infrastructure/           # Infrastructure as Code
│   └── Terraform/           # Terraform configs
└── archive/                  # Archived/unused files
```

## 🎯 Key Features

- **Dynamic User Context**: Switch between demo users (Catherine Liu, Ingrid Zhou, Demo User)
- **Smart RAG Filtering**: Automatically filters irrelevant customer data and tier-specific information
- **Enhanced Prompt Engineering**: Context-aware prompts with tier validation
- **Real-time Metrics**: Grounding, relevance, and factual accuracy scoring
- **LaunchDarkly Integration**: AI configs, feature flags, and experimentation
- **AWS Bedrock**: Claude/Nova models with guardrails for safety

## 🔧 API Endpoints

- `GET /api/current-user` - Get current demo user
- `POST /api/switch-user?user_key=<key>` - Switch demo user
- `POST /api/chat` - Chat with the RAG system
- `POST /api/chatbotfeedback` - Submit feedback
- `GET /health` - Health check

## 🧪 Testing the RAG Improvements

1. Ask: "how do i avoid overdraft fees?"
2. Check metrics for:
   - High grounding score (>80%)
   - Good factual accuracy (>70%)
   - Personalized response for current user tier
3. Switch users and see different responses:
   ```bash
   curl -X POST "http://localhost:8000/api/switch-user?user_key=ingrid_zhou"
   ```

## 📚 Documentation

- **Setup Guide**: `docs/SETUP_CREDENTIALS.md`
- **UX Documentation**: `docs/TOGGLEBANK_UX_README.md`
- **Original README**: `docs/README.md`

## 🔑 Environment Variables

Create a `.env` file with:
```
LAUNCHDARKLY_SDK_KEY=sdk-...
LAUNCHDARKLY_AI_CONFIG_KEY=toggle-bank-rag
LAUNCHDARKLY_LLM_JUDGE_KEY=llm-as-judge
LD_API_TOKEN=api-...
LAUNCHDARKLY_PROJECT_KEY=mpoliks-ld-demo
LAUNCHDARKLY_ENVIRONMENT_KEY=production
LAUNCHDARKLY_FLAG_KEY=toggle-bank-rag
AWS_REGION=us-east-1
```

## 🏗️ Architecture

- **Frontend**: Next.js with React, Tailwind CSS
- **Backend**: FastAPI with Python
- **AI**: LaunchDarkly AI Configs + AWS Bedrock
- **RAG**: AWS Knowledge Base with vector search
- **Safety**: AWS Bedrock Guardrails
- **Evaluation**: LLM-as-a-Judge for factual accuracy

---

Built with ❤️ using LaunchDarkly AI, AWS Bedrock, and modern web technologies. 
