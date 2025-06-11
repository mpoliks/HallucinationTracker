# ToggleBank UX Integration

This project combines your **Python RAG chatbot** with the **official ToggleBank frontend design** to create a professional, enterprise-ready chat experience.

## 🎯 What This Gives You

- **Exact ToggleBank branding and UI** - Professional banking interface
- **Your Python chatbot logic** - RAG + Guardrails + LLM-judge intact
- **LaunchDarkly AI configs** - Full feature flag integration
- **Real-time chat** - Modern streaming chat experience
- **Responsive design** - Works on desktop and mobile
- **Feedback system** - Thumbs up/down tracking

## 🏗️ Architecture

```
┌─────────────────┐    HTTP calls    ┌─────────────────┐
│   ToggleBank    │ ────────────────► │   Python        │
│   Frontend      │                  │   FastAPI       │
│   (Next.js)     │ ◄──────────────── │   Backend       │
│   Port 3000     │    JSON response │   Port 8000     │
└─────────────────┘                  └─────────────────┘
         │                                     │
         │                                     │
         ▼                                     ▼
┌─────────────────┐                  ┌─────────────────┐
│   Chat UI       │                  │   Your RAG      │
│   Components    │                  │   + Guardrails  │
│   + Branding    │                  │   + LLM Judge   │
└─────────────────┘                  └─────────────────┘
```

## 🚀 Quick Start

### 1. Setup (One Time)
```bash
python setup_togglebank_ux.py
```

### 2. Run the Application

**Terminal 1 - Python Backend:**
```bash
python fastapi_wrapper.py
```

**Terminal 2 - ToggleBank Frontend:**
```bash
npm run dev
```

**Open Browser:**
- Go to `http://localhost:3000`
- Click the floating chat icon (bottom right)
- Start chatting! 🤖

## 📁 Key Files

### Python Backend
- `fastapi_wrapper.py` - FastAPI wrapper around your chatbot
- `script.py` - Your original chatbot logic (unchanged)

### Frontend Integration
- `pages/api/chat.ts` - Modified to call Python backend
- `pages/api/chatbotfeedback.ts` - Modified for feedback handling
- `components/chatbot/ChatBot.tsx` - ToggleBank chat UI (unchanged)

## 🔧 Configuration

### Python (.env)
```env
LAUNCHDARKLY_SDK_KEY=sdk-xxx
LAUNCHDARKLY_AI_CONFIG_KEY=ai-config-xxx
LAUNCHDARKLY_LLM_JUDGE_KEY=judge-xxx
AWS_REGION=us-east-1
# Your AWS credentials...
```

### Frontend (.env.local)
```env
PYTHON_API_URL=http://localhost:8000
LD_SDK_KEY=your_launchdarkly_sdk_key
```

## 🎨 UI Features

### Chat Interface
- **Professional ToggleBank branding**
- **Real-time message streaming**
- **Typing indicators and loading states**
- **Mobile-responsive design**
- **Model and configuration display**

### Feedback System
- **Thumbs up/down buttons**
- **Automatic LaunchDarkly tracking**
- **User satisfaction metrics**

### Banking Context
- **Catherine Liu persona integration**
- **Customer tier and location context**
- **Personalized RAG query enhancement**

## 🔄 API Endpoints

### Python FastAPI Backend

#### Chat Endpoint
```
POST http://localhost:8000/api/chat
```
```json
{
  "aiConfigKey": "your-ai-config-key",
  "userInput": "What's my account balance?"
}
```

#### Feedback Endpoint
```
POST http://localhost:8000/api/chatbotfeedback
```
```json
{
  "feedback": "AI_CHATBOT_GOOD_SERVICE",
  "aiConfigKey": "your-ai-config-key"
}
```

## 🧪 LaunchDarkly Integration

Your Python chatbot's LaunchDarkly features work exactly the same:

- **AI configs** - Model selection and prompts
- **Feature flags** - Enable/disable chatbot
- **Experimentation** - A/B test different models
- **Metrics tracking** - Accuracy, relevance, feedback
- **Custom parameters** - KB_ID, guardrail settings

## 🎯 Benefits vs Pure JavaScript Rewrite

| Approach | Time to Build | Risk | Features |
|----------|---------------|------|----------|
| **This Solution** | ✅ 1-2 days | ✅ Low risk | ✅ All features preserved |
| JavaScript Rewrite | ❌ 2-3 weeks | ❌ High risk | ❌ Feature loss risk |

## 🐛 Troubleshooting

### Python Backend Won't Start
- Check `.env` file exists with all required keys
- Verify AWS credentials are set
- Run `pip install -r requirements.txt`

### Frontend Won't Connect
- Ensure Python backend is running on port 8000
- Check `.env.local` has correct `PYTHON_API_URL`
- Verify `npm install` completed successfully

### Chat Not Working
- Check browser console for errors
- Verify LaunchDarkly keys are correct in both `.env` files
- Ensure your AI config in LaunchDarkly is enabled

## 📈 Next Steps

1. **Deploy to production** - Use Docker for easy deployment
2. **Add more pages** - Extend ToggleBank with additional features
3. **A/B testing** - Use LaunchDarkly to test different chat experiences
4. **Analytics** - Add dashboards for chat performance metrics

---

**Congratulations!** You now have a professional, enterprise-grade chat interface powered by your robust Python chatbot. 🎉 