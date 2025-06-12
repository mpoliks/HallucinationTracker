#!/usr/bin/env python3
"""
FastAPI wrapper for the existing Python chatbot to work with ToggleBank frontend
"""
import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from uuid import uuid4

# Import your existing chatbot components
import dotenv
import boto3
import ldclient
from ldclient.config import Config
from ldclient import Context
from ldai.client import LDAIClient, AIConfig, ModelConfig
from ldai.tracker import FeedbackKind

# Import functions from your existing script
from script import (
    get_kb_passages, 
    build_guardrail_prompt, 
    map_messages, 
    extract_system_messages,
    check_factual_accuracy as original_check_factual_accuracy,
    validate_response_for_user
)
from user_service import get_current_user_context, get_user_service

# Load environment
dotenv.load_dotenv()

# Debug environment loading
print(f"Debug: Environment variables loaded:")
print(f"  LAUNCHDARKLY_SDK_KEY: {os.getenv('LAUNCHDARKLY_SDK_KEY', 'NOT_FOUND')[:10]}..." if os.getenv('LAUNCHDARKLY_SDK_KEY') else "  LAUNCHDARKLY_SDK_KEY: NOT_FOUND")
print(f"  LAUNCHDARKLY_AI_CONFIG_KEY: {os.getenv('LAUNCHDARKLY_AI_CONFIG_KEY', 'NOT_FOUND')}")
print(f"  LAUNCHDARKLY_LLM_JUDGE_KEY: {os.getenv('LAUNCHDARKLY_LLM_JUDGE_KEY', 'NOT_FOUND')}")
print(f"  AWS_REGION: {os.getenv('AWS_REGION', 'NOT_FOUND')}")

app = FastAPI(title="ToggleBank Support Bot API")

# Enable CORS for the ToggleBank frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # ToggleBank frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LaunchDarkly and AWS clients (same as your script)
LD_SDK = os.getenv("LAUNCHDARKLY_SDK_KEY")
LD_KEY = os.getenv("LAUNCHDARKLY_AI_CONFIG_KEY")
LD_JUDGE_KEY = os.getenv("LAUNCHDARKLY_LLM_JUDGE_KEY")
REGION = os.getenv("AWS_REGION", "us-east-1")

ldclient.set_config(Config(LD_SDK))
ld = ldclient.get()
ai_client = LDAIClient(ld)

# AWS clients with SSO authentication
def initialize_aws_clients():
    """
    Initialize AWS clients using SSO profile 'marek'.
    This is the recommended secure authentication method.
    """
    import boto3
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ProfileNotFound, TokenRetrievalError
    
    region = os.getenv("AWS_REGION", "us-east-1")
    
    try:
        print("Debug: Using AWS SSO profile 'marek'...")
        session = boto3.Session(profile_name='marek', region_name=region)
        bedrock = session.client("bedrock-runtime")
        bedrock_agent = session.client("bedrock-agent-runtime")
        
        # Test the credentials with a simple API call
        import botocore
        try:
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            print(f"✅ Successfully authenticated as: {identity.get('Arn', 'Unknown')}")
            return bedrock, bedrock_agent
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] in ['InvalidUserID.NotFound', 'AccessDenied']:
                raise NoCredentialsError()
            raise
            
    except ProfileNotFound:
        print("\n❌ AWS SSO PROFILE ERROR:")
        print("═" * 50)
        print("AWS profile 'marek' not found.")
        print("\n🔧 SETUP REQUIRED:")
        print("   aws configure sso")
        print("   # Use profile name: marek")
        print("   # Use your SSO start URL: https://your-org.awsapps.com/start/#")
        print("   # Use region: us-east-1")
        print("═" * 50)
        raise Exception("AWS SSO profile 'marek' not configured")
        
    except TokenRetrievalError:
        print("\n❌ AWS SSO SESSION EXPIRED:")
        print("═" * 50)
        print("Your AWS SSO session has expired.")
        print("\n🔧 REFRESH REQUIRED:")
        print("   aws sso login --profile marek")
        print("   # This will open your browser to re-authenticate")
        print("═" * 50)
        raise Exception("AWS SSO session expired - please run: aws sso login --profile marek")
        
    except (NoCredentialsError, PartialCredentialsError) as e:
        print("\n❌ AWS SSO CREDENTIAL ERROR:")
        print("═" * 50)
        print(f"AWS SSO credentials issue: {e}")
        print("\n🔧 TROUBLESHOOTING:")
        print("   1. aws sso login --profile marek")
        print("   2. aws sts get-caller-identity --profile marek")
        print("   3. Check your SSO permissions")
        print("═" * 50)
        raise Exception(f"AWS SSO credentials failed: {e}")
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED AWS ERROR: {e}")
        print("═" * 50)
        print("🔧 DEBUG STEPS:")
        print("   1. aws sso login --profile marek")
        print("   2. aws configure list --profile marek")
        print("   3. Check your internet connection")
        print("═" * 50)
        raise Exception(f"Unexpected AWS error: {e}")

# Initialize AWS clients with improved error handling
try:
    bedrock, bedrock_agent = initialize_aws_clients()
except Exception as e:
    print(f"Failed to initialize AWS clients: {e}")
    sys.exit(1)

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    aiConfigKey: str
    userInput: str

class ChatResponse(BaseModel):
    response: str
    modelName: str
    enabled: bool
    requestId: str
    metrics: Dict[str, Any] = None
    pendingMetrics: bool = False
    error: str = None

class FeedbackRequest(BaseModel):
    feedback: str
    aiConfigKey: str

# User context now comes from the user service - no more hardcoding!
def get_user_context():
    """Get user context from the dynamic user service."""
    return get_current_user_context()

# Global store for async evaluation results
EVAL_RESULTS: Dict[str, Dict[str, Any]] = {}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Main chat endpoint that mirrors the ToggleBank frontend's expected behavior
    """
    try:
        context = get_user_context()
        
        # Default config - will be overridden by LaunchDarkly AI configs
        default_cfg = AIConfig(
            enabled=True, 
            model=ModelConfig(name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"), 
            messages=[]
        )

        # Get initial config to extract static parameters (KB_ID, GR_ID, etc.) - follow script.py pattern
        actual_ai_config_key = os.getenv("LAUNCHDARKLY_AI_CONFIG_KEY")
        print(f"Debug: LAUNCHDARKLY_AI_CONFIG_KEY from env: {actual_ai_config_key}")
        print(f"Debug: Request aiConfigKey: {request.aiConfigKey}")
        
        # Use the key from environment variable (like script.py does)
        if not actual_ai_config_key:
            print("Error: LAUNCHDARKLY_AI_CONFIG_KEY not found in environment!")
            actual_ai_config_key = request.aiConfigKey  # Fallback to request
            
        print(f"Debug: Using AI config key: {actual_ai_config_key}")
        # Get AI config with user input as variable for this specific query
        query_variables = {"userInput": request.userInput}
        cfg, tracker = ai_client.config(actual_ai_config_key, context, default_cfg, query_variables)
        
        # Get configuration values from LaunchDarkly AI config custom parameters using get_custom(key)
        print(f"Debug: Getting custom parameters individually...")
        try:
            KB_ID = cfg.model.get_custom('kb_id')
            GR_ID = cfg.model.get_custom('gr_id')
            GR_VER = str(cfg.model.get_custom('gr_version') or '1')
            print(f"Debug: KB_ID: {'***' if KB_ID else 'None'}, GR_ID: {'***' if GR_ID else 'None'}, GR_VER: {GR_VER}")
            custom_params = {
                'kb_id': KB_ID,
                'gr_id': GR_ID, 
                'gr_version': GR_VER,
                'eval_freq': cfg.model.get_custom('eval_freq') or '0.2'  # Reduce to 20% of requests
            }
        except Exception as e:
            print(f"Debug: get_custom(key) failed: {e}")
            # Fallback to old method
            config_dict = cfg.to_dict()
            model_config = config_dict.get('model', {})
            custom_params = model_config.get('custom') or {}
            KB_ID = custom_params.get('kb_id')
            GR_ID = custom_params.get('gr_id') 
            GR_VER = str(custom_params.get('gr_version', '1'))
            custom_params['eval_freq'] = custom_params.get('eval_freq', '0.2')  # Reduce to 20%
            print(f"Debug: Fallback - KB_ID: {'***' if KB_ID else 'None'}, GR_ID: {'***' if GR_ID else 'None'}, GR_VER: {GR_VER}")
        
        print(f"Using KB_ID: {'***' if KB_ID else 'None'}, GR_ID: {'***' if GR_ID else 'None'}, GR_VER: {GR_VER}, custom_params: {dict(custom_params, **{k: '***' if k in ['kb_id', 'gr_id'] and v else v for k, v in custom_params.items()})}")
        
        # Validate required parameters
        if not KB_ID:
            return ChatResponse(
                response="I'm sorry, kb_id not found in LaunchDarkly AI config custom parameters.",
                modelName="",
                enabled=True,
                error="Missing kb_id configuration",
                requestId=str(uuid4())
            )
        if not GR_ID:
            return ChatResponse(
                response="I'm sorry, gr_id not found in LaunchDarkly AI config custom parameters.",
                modelName="",
                enabled=True,
                error="Missing gr_id configuration",
                requestId=str(uuid4())
            )

        if not cfg.enabled:
            return ChatResponse(
                response="I'm sorry, the service is currently disabled.",
                modelName="",
                enabled=False,
                requestId=str(uuid4())
            )

        # Use the model from LaunchDarkly AI config
        model_id = cfg.model.name
        print(f"Debug: Using model from LaunchDarkly config: {model_id}")
        history = list(cfg.messages) if cfg.messages else []

        # Enhanced RAG query strategy with user context and tier information
        user_context_name = context.name
        context_dict = context.to_dict()
        user_tier = context_dict.get("tier", "")
        
        if any(word in request.userInput.lower() for word in ["my", "i", "me", "mine"]):
            # Personal queries should include the user's name and tier for better RAG results
            enhanced_query = f"{user_context_name} {user_tier} tier {request.userInput}"
        else:
            # Non-personal queries include tier for relevant policy information
            enhanced_query = f"{user_tier} tier {request.userInput}"
            
        passages = get_kb_passages(enhanced_query, KB_ID, bedrock_agent, context)
        
        # Validate that we have relevant passages for this user
        if "No relevant passages found" in passages:
            # Try a broader search without user context
            fallback_query = request.userInput
            passages = get_kb_passages(fallback_query, KB_ID, bedrock_agent, context)
            if "No relevant passages found" in passages:
                passages = "I don't have specific information about that topic in my knowledge base. Please contact ToggleSupport via chat or phone for personalized assistance."
        context_dict = context.to_dict()
        prompt = build_guardrail_prompt(passages, request.userInput, context_dict)

        # Assemble conversation in Bedrock's expected format
        user_content = [
            {
                "guardContent": {
                    "text": {
                        "text": passages,
                        "qualifiers": ["grounding_source"]
                    }
                }
            },
            {
                "guardContent": {
                    "text": {
                        "text": request.userInput,
                        "qualifiers": ["query"]
                    }
                }
            }
        ]
        
        convo_msgs = map_messages(history) + [{"role": "user", "content": user_content}]
        system_msgs = extract_system_messages(history)

        # Build converse parameters
        converse_params = {
            "modelId": model_id,
            "messages": convo_msgs,
            "guardrailConfig": {                            
                "guardrailIdentifier": GR_ID,
                "guardrailVersion": GR_VER,
                "trace": "enabled", 
            },
        }
        
        if system_msgs:
            converse_params["system"] = system_msgs

        print(f"Debug: About to call bedrock.converse with model: {converse_params['modelId']}")
        # Call Bedrock and track with SDK
        raw = bedrock.converse(**converse_params)
        
        # Extract metrics from guardrail trace
        metrics = {}
        if "trace" in raw and "guardrail" in raw["trace"]:
            guardrail_trace = raw["trace"]["guardrail"]
            print(f"Debug: Guardrail trace found: {json.dumps(guardrail_trace, indent=2)}")
            
            # Extract metrics from output assessments
            if "outputAssessments" in guardrail_trace:
                for gr_id, assessments in guardrail_trace["outputAssessments"].items():
                    if assessments and len(assessments) > 0:
                        assessment = assessments[0]
                        
                        # Extract grounding and relevance scores
                        if "contextualGroundingPolicy" in assessment:
                            filters = assessment["contextualGroundingPolicy"].get("filters", [])
                            for filter_item in filters:
                                if filter_item.get("type") == "GROUNDING":
                                    metrics["grounding_score"] = filter_item.get("score", 0)
                                    metrics["grounding_threshold"] = filter_item.get("threshold", 0)
                                elif filter_item.get("type") == "RELEVANCE":
                                    metrics["relevance_score"] = filter_item.get("score", 0)
                                    metrics["relevance_threshold"] = filter_item.get("threshold", 0)
                        
                        # Extract processing metrics
                        if "invocationMetrics" in assessment:
                            inv_metrics = assessment["invocationMetrics"]
                            metrics["processing_latency_ms"] = inv_metrics.get("guardrailProcessingLatency", 0)
                            
                            # Extract usage metrics
                            if "usage" in inv_metrics:
                                usage = inv_metrics["usage"]
                                metrics["contextual_grounding_units"] = usage.get("contextualGroundingPolicyUnits", 0)
                            
                            # Extract coverage metrics
                            if "guardrailCoverage" in inv_metrics:
                                coverage = inv_metrics["guardrailCoverage"]
                                if "textCharacters" in coverage:
                                    text_chars = coverage["textCharacters"]
                                    metrics["characters_guarded"] = text_chars.get("guarded", 0)
                                    metrics["total_characters"] = text_chars.get("total", 0)
                        break
        else:
            print("Debug: No guardrail trace information found")
        
        # Add model information to metrics
        metrics["model_used"] = model_id
        metrics["knowledge_base_id"] = KB_ID
        metrics["guardrail_id"] = GR_ID
        
        # Add token usage from main response
        usage = raw.get("usage", {})
        metrics["input_tokens"] = usage.get("inputTokens")
        metrics["output_tokens"] = usage.get("outputTokens")
        
        print(f"Debug: Final metrics object before factual check: {json.dumps(metrics, indent=2)}")
        
        # Use provider-specific tracking method for Bedrock
        if tracker:
            tracker.track_bedrock_converse_metrics(raw)
        
        # Extract response text
        reply_txt = raw["output"]["message"]["content"][0]["text"]
        
        # Validate response for user-specific accuracy
        reply_txt = validate_response_for_user(reply_txt, context)
        
        # Generate a unique request ID for this chat
        request_id = str(uuid4())
        print(f"Debug: Generated request_id {request_id} for async processing")
        
        # Store the basic metrics we already have
        EVAL_RESULTS[request_id] = None  # placeholder to indicate metrics are pending
        
        # Launch judge evaluation in background
        background_tasks.add_task(
            _run_judge_async,
            request_id,
            passages=passages,
            reply_txt=reply_txt,
            user_question=request.userInput,
            model_id=model_id,
            custom_params=custom_params,
            context=context,
            guardrail_metrics=metrics.copy()
        )
        
        # Explicitly remove any judge-related metrics
        # This ensures we only return guardrail metrics in the initial response
        judge_metrics = [
            "factual_accuracy_score", 
            "judge_model_name", 
            "judge_input_tokens", 
            "judge_output_tokens",
            "judge_reasoning",
            "factual_claims",
            "accurate_claims",
            "inaccurate_claims"
        ]
        
        for key in judge_metrics:
            if key in metrics:
                del metrics[key]
        
        # Return immediately with the response and basic metrics
        return ChatResponse(
            response=reply_txt,
            modelName=model_id,
            enabled=True,
            requestId=request_id,
            metrics=metrics,  # only include guardrail metrics, not judge metrics
            pendingMetrics=True  # indicate that full metrics are still being processed
        )

    except Exception as e:
        logging.error(f"Error in chat endpoint: {e}")
        # Consider more specific error handling
        return ChatResponse(
            response="An unexpected error occurred.",
            modelName="",
            enabled=True,
            error=str(e),
            requestId=str(uuid4())
        )

# Simple Message class for compatibility with your script's logic
class SimpleMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
    
    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content
        }

@app.post("/api/chatbotfeedback")
async def feedback_endpoint(request: FeedbackRequest):
    """
    Feedback endpoint for thumbs up/down responses
    """
    try:
        context = get_user_context()
        
        # Get AI config for tracking
        default_cfg = AIConfig(enabled=True, model=ModelConfig(name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"), messages=[])
        cfg, tracker = ai_client.config(request.aiConfigKey, context, default_cfg, {})
        
        # Track feedback
        if request.feedback == "AI_CHATBOT_GOOD_SERVICE":
            tracker.track_feedback({"kind": FeedbackKind.Positive})
        elif request.feedback == "AI_CHATBOT_BAD_SERVICE":
            tracker.track_feedback({"kind": FeedbackKind.Negative})
        
        ld.flush()
        
        return {"status": "success", "message": "Feedback received"}
        
    except Exception as e:
        logging.error(f"Error in feedback endpoint: {e}")
        return {"error": str(e)}

@app.post("/api/switch-user")
async def switch_user(user_key: str):
    """
    Switch to a different demo user for testing purposes.
    In production, this would be handled by authentication.
    
    Args:
        user_key: User identifier (e.g., "catherine_liu", "ingrid_zhou", "demo_user")
    """
    try:
        user_service = get_user_service()
        success = user_service.set_current_user(user_key)
        
        if success:
            current_profile = user_service.get_current_user_profile()
            return {
                "status": "success", 
                "message": f"Switched to user: {current_profile['name']}",
                "user_profile": current_profile
            }
        else:
            available_users = user_service.get_available_users()
            return {
                "status": "error",
                "message": f"User '{user_key}' not found",
                "available_users": available_users
            }
    except Exception as e:
        logging.error(f"Error switching user: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/current-user")
async def get_current_user():
    """Get information about the current demo user."""
    try:
        user_service = get_user_service()
        profile = user_service.get_current_user_profile()
        available_users = user_service.get_available_users()
        
        return {
            "current_user": profile,
            "available_users": available_users
        }
    except Exception as e:
        logging.error(f"Error getting current user: {e}")
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ToggleBank Support Bot API"}

# Create a wrapper function that skips the judge evaluation
def check_factual_accuracy(source_passages: str, response_text: str, user_question: str, generator_model_id: str, custom_params: dict, context: Context, ai_client: LDAIClient, bedrock) -> dict:
    """
    Wrapper for check_factual_accuracy that skips the actual judge evaluation for async processing.
    The real evaluation will happen in the background task.
    """
    # For the initial response, return only basic metrics without judge evaluation
    return {}

# helper to run judge in background
async def _run_judge_async(request_id: str, *, passages: str, reply_txt: str, user_question: str, model_id: str, custom_params: dict, context: Context, guardrail_metrics: dict):
    """Run the judge evaluation in a background task"""
    try:
        print(f"Debug: Running judge in background for request {request_id}")
        # Create a context copy with the user question
        context_dict = context.to_dict()
        context_dict["lastUserInput"] = user_question
        
        # Use the original function from script.py
        judge_breakdown = await asyncio.to_thread(
            original_check_factual_accuracy,
            source_passages=passages,
            response_text=reply_txt,
            user_question=user_question,
            generator_model_id=model_id,
            custom_params=custom_params,
            context=context,
            ai_client=ai_client,
            bedrock=bedrock
        )
        print(f"Debug: Judge completed for request {request_id}")
        accuracy = (judge_breakdown or {}).get("accuracy_score")
        jd_copy = dict(judge_breakdown or {})
        # Remove duplicate to keep insertion order clean
        if "accuracy_score" in jd_copy:
            jd_copy.pop("accuracy_score")
        combined_metrics = {"accuracy_score": accuracy, "factual_accuracy_score": accuracy, **guardrail_metrics, **jd_copy}
        EVAL_RESULTS[request_id] = combined_metrics
    except Exception as e:
        print(f"Debug: Judge error for request {request_id}: {e}")
        # Preserve guardrail metrics even in error case and set hallucination_score to None
        combined_metrics = {**guardrail_metrics, "judge_error": str(e), "factual_accuracy_score": None}
        EVAL_RESULTS[request_id] = combined_metrics

# new endpoint
@app.get("/api/chat-metrics")
async def get_chat_metrics(request_id: str):
    if request_id not in EVAL_RESULTS:
        return {"status": "unknown"}
    if EVAL_RESULTS[request_id] is None:
        return {"status": "pending"}
    return {"status": "ready", "metrics": EVAL_RESULTS.pop(request_id)}

@app.post("/api/chat-async", response_model=ChatResponse)
async def chat_endpoint_async(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Async version of the chat endpoint that returns immediately with guardrail metrics only
    and processes judge evaluation in the background.
    """
    try:
        context = get_user_context()
        
        # Default config - will be overridden by LaunchDarkly AI configs
        default_cfg = AIConfig(
            enabled=True, 
            model=ModelConfig(name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"), 
            messages=[]
        )

        # Get initial config to extract static parameters (KB_ID, GR_ID, etc.)
        actual_ai_config_key = os.getenv("LAUNCHDARKLY_AI_CONFIG_KEY")
        print(f"Debug: LAUNCHDARKLY_AI_CONFIG_KEY from env: {actual_ai_config_key}")
        print(f"Debug: Request aiConfigKey: {request.aiConfigKey}")
        
        # Use the key from environment variable
        if not actual_ai_config_key:
            print("Error: LAUNCHDARKLY_AI_CONFIG_KEY not found in environment!")
            actual_ai_config_key = request.aiConfigKey  # Fallback to request
            
        print(f"Debug: Using AI config key: {actual_ai_config_key}")
        # Get AI config with user input as variable for this specific query
        query_variables = {"userInput": request.userInput}
        cfg, tracker = ai_client.config(actual_ai_config_key, context, default_cfg, query_variables)
        
        # Get configuration values from LaunchDarkly AI config custom parameters
        print(f"Debug: Getting custom parameters individually...")
        try:
            KB_ID = cfg.model.get_custom('kb_id')
            GR_ID = cfg.model.get_custom('gr_id')
            GR_VER = str(cfg.model.get_custom('gr_version') or '1')
            print(f"Debug: KB_ID: {'***' if KB_ID else 'None'}, GR_ID: {'***' if GR_ID else 'None'}, GR_VER: {GR_VER}")
            custom_params = {
                'kb_id': KB_ID,
                'gr_id': GR_ID, 
                'gr_version': GR_VER,
                'eval_freq': cfg.model.get_custom('eval_freq') or '0.2'
            }
        except Exception as e:
            print(f"Debug: get_custom(key) failed: {e}")
            # Fallback to old method
            config_dict = cfg.to_dict()
            model_config = config_dict.get('model', {})
            custom_params = model_config.get('custom') or {}
            KB_ID = custom_params.get('kb_id')
            GR_ID = custom_params.get('gr_id') 
            GR_VER = str(custom_params.get('gr_version', '1'))
            custom_params['eval_freq'] = custom_params.get('eval_freq', '0.2')
            print(f"Debug: Fallback - KB_ID: {'***' if KB_ID else 'None'}, GR_ID: {'***' if GR_ID else 'None'}, GR_VER: {GR_VER}")
        
        print(f"Using KB_ID: {'***' if KB_ID else 'None'}, GR_ID: {'***' if GR_ID else 'None'}, GR_VER: {GR_VER}, custom_params: {dict(custom_params, **{k: '***' if k in ['kb_id', 'gr_id'] and v else v for k, v in custom_params.items()})}")
        
        # Validate required parameters
        if not KB_ID:
            return ChatResponse(
                response="I'm sorry, kb_id not found in LaunchDarkly AI config custom parameters.",
                modelName="",
                enabled=True,
                error="Missing kb_id configuration",
                requestId=str(uuid4())
            )
        if not GR_ID:
            return ChatResponse(
                response="I'm sorry, gr_id not found in LaunchDarkly AI config custom parameters.",
                modelName="",
                enabled=True,
                error="Missing gr_id configuration",
                requestId=str(uuid4())
            )

        if not cfg.enabled:
            return ChatResponse(
                response="I'm sorry, the service is currently disabled.",
                modelName="",
                enabled=False,
                requestId=str(uuid4())
            )

        # Use the model from LaunchDarkly AI config
        model_id = cfg.model.name
        print(f"Debug: Using model from LaunchDarkly config: {model_id}")
        history = list(cfg.messages) if cfg.messages else []

        # Enhanced RAG query strategy with user context and tier information
        user_context_name = context.name
        context_dict = context.to_dict()
        user_tier = context_dict.get("tier", "")
        
        if any(word in request.userInput.lower() for word in ["my", "i", "me", "mine"]):
            # Personal queries should include the user's name and tier for better RAG results
            enhanced_query = f"{user_context_name} {user_tier} tier {request.userInput}"
        else:
            # Non-personal queries include tier for relevant policy information
            enhanced_query = f"{user_tier} tier {request.userInput}"
            
        passages = get_kb_passages(enhanced_query, KB_ID, bedrock_agent, context)
        
        # Validate that we have relevant passages for this user
        if "No relevant passages found" in passages:
            # Try a broader search without user context
            fallback_query = request.userInput
            passages = get_kb_passages(fallback_query, KB_ID, bedrock_agent, context)
            if "No relevant passages found" in passages:
                passages = "I don't have specific information about that topic in my knowledge base. Please contact ToggleSupport via chat or phone for personalized assistance."
        
        prompt = build_guardrail_prompt(passages, request.userInput, context_dict)

        # Assemble conversation in Bedrock's expected format
        user_content = [
            {
                "guardContent": {
                    "text": {
                        "text": passages,
                        "qualifiers": ["grounding_source"]
                    }
                }
            },
            {
                "guardContent": {
                    "text": {
                        "text": request.userInput,
                        "qualifiers": ["query"]
                    }
                }
            }
        ]
        
        convo_msgs = map_messages(history) + [{"role": "user", "content": user_content}]
        system_msgs = extract_system_messages(history)

        # Build converse parameters
        converse_params = {
            "modelId": model_id,
            "messages": convo_msgs,
            "guardrailConfig": {                            
                "guardrailIdentifier": GR_ID,
                "guardrailVersion": GR_VER,
                "trace": "enabled", 
            },
        }
        
        if system_msgs:
            converse_params["system"] = system_msgs

        print(f"Debug: About to call bedrock.converse with model: {converse_params['modelId']}")
        # Call Bedrock and track with SDK
        raw = bedrock.converse(**converse_params)
        
        # Extract metrics from guardrail trace
        metrics = {}
        if "trace" in raw and "guardrail" in raw["trace"]:
            guardrail_trace = raw["trace"]["guardrail"]
            print(f"Debug: Guardrail trace found: {json.dumps(guardrail_trace, indent=2)}")
            
            # Extract metrics from output assessments
            if "outputAssessments" in guardrail_trace:
                for gr_id, assessments in guardrail_trace["outputAssessments"].items():
                    if assessments and len(assessments) > 0:
                        assessment = assessments[0]
                        
                        # Extract grounding and relevance scores
                        if "contextualGroundingPolicy" in assessment:
                            filters = assessment["contextualGroundingPolicy"].get("filters", [])
                            for filter_item in filters:
                                if filter_item.get("type") == "GROUNDING":
                                    metrics["grounding_score"] = filter_item.get("score", 0)
                                    metrics["grounding_threshold"] = filter_item.get("threshold", 0)
                                elif filter_item.get("type") == "RELEVANCE":
                                    metrics["relevance_score"] = filter_item.get("score", 0)
                                    metrics["relevance_threshold"] = filter_item.get("threshold", 0)
                        
                        # Extract processing metrics
                        if "invocationMetrics" in assessment:
                            inv_metrics = assessment["invocationMetrics"]
                            metrics["processing_latency_ms"] = inv_metrics.get("guardrailProcessingLatency", 0)
                            
                            # Extract usage metrics
                            if "usage" in inv_metrics:
                                usage = inv_metrics["usage"]
                                metrics["contextual_grounding_units"] = usage.get("contextualGroundingPolicyUnits", 0)
                            
                            # Extract coverage metrics
                            if "guardrailCoverage" in inv_metrics:
                                coverage = inv_metrics["guardrailCoverage"]
                                if "textCharacters" in coverage:
                                    text_chars = coverage["textCharacters"]
                                    metrics["characters_guarded"] = text_chars.get("guarded", 0)
                                    metrics["total_characters"] = text_chars.get("total", 0)
                        break
        else:
            print("Debug: No guardrail trace information found")
        
        # Add model information to metrics
        metrics["model_used"] = model_id
        metrics["knowledge_base_id"] = KB_ID
        metrics["guardrail_id"] = GR_ID
        
        # Add token usage from main response
        usage = raw.get("usage", {})
        metrics["input_tokens"] = usage.get("inputTokens")
        metrics["output_tokens"] = usage.get("outputTokens")
        
        print(f"Debug: Final metrics object: {json.dumps(metrics, indent=2)}")
        
        # Use provider-specific tracking method for Bedrock
        if tracker:
            tracker.track_bedrock_converse_metrics(raw)
        
        # Extract response text
        reply_txt = raw["output"]["message"]["content"][0]["text"]
        
        # Validate response for user-specific accuracy
        reply_txt = validate_response_for_user(reply_txt, context)
        
        # Generate a unique request ID for this chat
        request_id = str(uuid4())
        print(f"Debug: Generated request_id {request_id} for async processing")
        
        # Store the basic metrics we already have
        EVAL_RESULTS[request_id] = None  # placeholder to indicate metrics are pending
        
        # Launch judge evaluation in background
        background_tasks.add_task(
            _run_judge_async,
            request_id,
            passages=passages,
            reply_txt=reply_txt,
            user_question=request.userInput,
            model_id=model_id,
            custom_params=custom_params,
            context=context,
            guardrail_metrics=metrics.copy()
        )
        
        # Return immediately with the response and basic metrics
        return ChatResponse(
            response=reply_txt,
            modelName=model_id,
            enabled=True,
            requestId=request_id,
            metrics=metrics,  # only include guardrail metrics, not judge metrics
            pendingMetrics=True  # indicate that full metrics are still being processed
        )

    except Exception as e:
        logging.error(f"Error in chat endpoint: {e}")
        # Consider more specific error handling
        return ChatResponse(
            response="An unexpected error occurred.",
            modelName="",
            enabled=True,
            error=str(e),
            requestId=str(uuid4())
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 