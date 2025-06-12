# ToggleBank RAG System

A comprehensive RAG (Retrieval-Augmented Generation) chatbot system for ToggleBank with LaunchDarkly AI integration, AWS Bedrock, and dynamic user management.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- AWS CLI configured with SSO profile 'marek'
- LaunchDarkly account with AI configs

### Running the Application

Run make or make reset. 
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