# HallucinationTracker

A terminal-based RAG (Retrieval-Augmented Generation) chat bot with integrated hallucination detection and relevance scoring using LaunchDarkly AI Configs and AWS Bedrock Guardrails.

## Features

- 🚀 **LaunchDarkly AI Configs** - Centralized prompt/model governance and experimentation
- 🔍 **AWS Bedrock Knowledge Base** - Vector search-based RAG retrieval
- 🛡️ **AWS Bedrock Guardrails** - Real-time hallucination & relevance detection
- 📊 **Live Metrics & Feedback** - Automatic tracking sent back to LaunchDarkly
- 🎯 **Experimentation Ready** - A/B test different models, guardrails, and knowledge bases

## Architecture

```
User Query → Knowledge Base Retrieval → Contextualized Prompt → Bedrock LLM + Guardrails → Response + Metrics → LaunchDarkly
```

## Prerequisites

- Python 3.8+
- AWS Account with access to:
  - Bedrock (Claude models)
  - Bedrock Knowledge Base
  - Bedrock Guardrails
- LaunchDarkly account with AI Configs enabled

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mpoliks/HallucinationTracker.git
   cd HallucinationTracker
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   LAUNCHDARKLY_SDK_KEY=sdk-your-key-here
   LAUNCHDARKLY_AI_CONFIG_KEY=your-ai-config-key
   AWS_REGION=us-east-1
   ```

4. **Configure LaunchDarkly AI Config:**
   Set up your AI Config with custom parameters:
   ```json
   {
     "enabled": true,
     "model": {
       "name": "us.anthropic.claude-3-haiku-20240307-v1:0",
       "parameters": {
         "max_tokens": 1000,
         "temperature": 0.5,
         "top_p": 0.5
       },
       "custom": {
         "kb_id": "YOUR_KNOWLEDGE_BASE_ID",
         "gr_id": "YOUR_GUARDRAIL_ID", 
         "gr_version": "1"
       }
     },
     "messages": [
       {
         "role": "system",
         "content": "Your system prompt here..."
       }
     ],
     "provider": {
       "name": "Anthropic"
     }
   }
   ```

## Usage

Run the chat bot:
```bash
python script.py
```

The bot will:
1. Connect to LaunchDarkly and retrieve your AI configuration
2. Display the current model, guardrail, and knowledge base settings
3. Start an interactive chat session
4. For each query:
   - Retrieve relevant passages from your knowledge base
   - Send contextualized prompt to Bedrock with guardrails enabled
   - Display the response with hallucination/relevance scores
   - Request user feedback
   - Send metrics back to LaunchDarkly for experimentation

## Configuration Parameters

### LaunchDarkly AI Config Custom Parameters

- **`kb_id`** (required): AWS Bedrock Knowledge Base ID
- **`gr_id`** (required): AWS Bedrock Guardrail ID  
- **`gr_version`** (optional): Guardrail version (defaults to "DRAFT")

### Metrics Tracked

- **Success/Error rates** - Request completion status
- **Latency** - Response time in milliseconds
- **Token usage** - Input/output token consumption
- **Time to first token** - Response latency
- **Hallucination scores** - Contextual grounding accuracy (0-1)
- **Relevance scores** - Query-response relevance (0-1)
- **User feedback** - Positive/negative ratings

## Experimentation

Use LaunchDarkly's targeting and experimentation features to:

- **A/B test different models** (Claude 3 Haiku vs Sonnet vs Opus)
- **Compare guardrail configurations** 
- **Test different knowledge bases**
- **Optimize model parameters** (temperature, top_p, max_tokens)
- **Measure hallucination rates** across configurations
- **Track user satisfaction** by segment

## Dependencies

- `boto3` - AWS SDK for Bedrock integration
- `ldclient-py` - LaunchDarkly Python SDK
- `ldai` - LaunchDarkly AI SDK
- `python-dotenv` - Environment variable management

## License

MIT License - See LICENSE file for details 