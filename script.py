#!/usr/bin/env python3
"""
chat_rag_guardrail.py – Terminal chat bot with:
  • LaunchDarkly AI Configs           – prompt/model governance
  • S3-backed RAG retrieval           – reference source
  • Bedrock inline guardrail          – hallucination & relevance check
  • Live metrics & user feedback      – sent back to LaunchDarkly

Keys come from .env in the same folder.
"""
import os, sys, json, signal, hashlib, logging, textwrap, time, uuid
from typing import List, Dict, Any

import dotenv, boto3, botocore
import ldclient
from ldclient.config import Config
from ldclient import Context
from ldai.client import LDAIClient, AIConfig, ModelConfig
from ldai.tracker import FeedbackKind, TokenUsage

# ── setup & helpers ───────────────────────────────────────────────────────────
dotenv.load_dotenv()

LD_SDK   = os.getenv("LAUNCHDARKLY_SDK_KEY")
LD_KEY   = os.getenv("LAUNCHDARKLY_AI_CONFIG_KEY")
REGION   = os.getenv("AWS_REGION", "us-east-1")

# These will now come from LaunchDarkly AI config instead of env vars
# GR_ID    = os.getenv("AWS_GUARDRAIL_ID")
# GR_VER   = os.getenv("AWS_GUARDRAIL_VERSION", "DRAFT")
# KB_ID    = os.getenv("RAG_BUCKET")  
# PREFIX   = os.getenv("RAG_PREFIX", "rag/passages/")  

if not (LD_SDK and LD_KEY):
    sys.exit("✖  Missing required env vars – check your .env file")

# LD initialisation
ldclient.set_config(Config(LD_SDK))
ld = ldclient.get()
if not ld.is_initialized():
    sys.exit("✖  LaunchDarkly SDK failed to initialise")

ai_client = LDAIClient(ld)

# AWS clients
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=REGION)
s3      = boto3.client("s3",              region_name=REGION)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")

def print_box(title: str, text: str) -> None:
    lines = textwrap.wrap(text, 78)
    width = max(len(title), *(len(l) for l in lines)) + 4
    print("┌" + "─"*width + "┐")
    print("│ " + title.center(width-2) + " │")
    print("├" + "─"*width + "┤")
    for l in lines:
        print("│ " + l.ljust(width-2) + " │")
    print("└" + "─"*width + "┘")

def s3_get_passages(question: str, kb_id: str) -> str:
    """
    Query AWS Bedrock Knowledge Base using vector search
    """
    try:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=kb_id,  # Now passed as parameter
            retrievalQuery={
                'text': question
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 20  # Increased from 10 to 20 for more comprehensive context
                }
            }
        )
        
        # Extract and concatenate retrieved passages
        passages = []
        for result in response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            if content:
                passages.append(content)
        
        if passages:
            return '\n\n---\n\n'.join(passages)
        else:
            return "No relevant passages found."
            
    except botocore.exceptions.ClientError as e:
        logging.error("Knowledge Base retrieval error: %s", e)
        return "Error retrieving passages from knowledge base."

def map_messages(msgs) -> List[Dict[str, Any]]:
    """Convert messages, filtering out system messages for separate handling"""
    return [{"role": m.role, "content": [{"text": m.content}]} 
            for m in msgs if m.role in ["user", "assistant"]]

def extract_system_messages(msgs) -> List[Dict[str, str]]:
    """Extract system messages for the system parameter"""
    return [{"text": m.content} for m in msgs if m.role == "system"]

def build_guardrail_prompt(passages: str, question: str) -> str:
    # Try a format that may trigger contextual grounding better
    return (
        f"Given the following source information:\n\n{passages}\n\n"
        f"Question: {question}\n\n"
        f"Please answer based only on the provided source information."
    )

# Simple Message class to match expected structure
class SimpleMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

# graceful Ctrl-C
signal.signal(signal.SIGINT, lambda *_: sys.exit("\n👋  bye!"))

# ── main loop ────────────────────────────────────────────────────────────────
def main() -> None:
    # Generate unique user for fresh experiment exposure each time
    unique_user_key = f"user-{uuid.uuid4().hex[:8]}"
    context = Context.builder(unique_user_key).kind("user").name(f"CLI Tester {unique_user_key}").build()
    
    # Enhanced default config with model details for better tracking
    default_cfg = AIConfig(
        enabled=True, 
        model=ModelConfig(name="us.anthropic.claude-3-haiku-20240307-v1:0"), 
        messages=[]
    )

    cfg, tracker = ai_client.config(LD_KEY, context, default_cfg, {})
    
    # Get configuration values from LaunchDarkly AI config custom parameters
    # Custom parameters are stored under model.custom in the config dict
    config_dict = cfg.to_dict()
    model_config = config_dict.get('model', {})
    custom_params = model_config.get('custom', {})
    
    logging.info(f"Retrieved custom_params: {custom_params}")
    
    KB_ID = custom_params.get('kb_id')
    GR_ID = custom_params.get('gr_id') 
    GR_VER = custom_params.get('gr_version', 'DRAFT')
    
    # Validate required parameters
    if not KB_ID:
        logging.error(f"kb_id not found. custom_params: {custom_params}")
        sys.exit("✖  Missing kb_id in LaunchDarkly AI config custom parameters")
    if not GR_ID:
        logging.error(f"gr_id not found. custom_params: {custom_params}")
        sys.exit("✖  Missing gr_id in LaunchDarkly AI config custom parameters")
    
    # Debug the configuration
    logging.info(f"AI Config received: enabled={cfg.enabled}, model={cfg.model}")
    logging.info(f"Custom params: kb_id={KB_ID}, gr_id={GR_ID}, gr_version={GR_VER}")
    
    model_id = cfg.model.name if cfg.model else "us.anthropic.claude-3-haiku-20240307-v1:0"
    history  = list(cfg.messages) if cfg.messages else []   # seed messages from LD

    logging.info(f"Generated unique user: {unique_user_key}")
    print_box("READY", f"User: {unique_user_key}\nMLOps model: {model_id}\nGuardrail: {GR_ID}@v{GR_VER}\nKnowledge Base: {KB_ID}\nType 'exit' to quit.")

    while True:
        user = input("\n🧑  You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break

        passages = s3_get_passages(user, KB_ID)
        print_box("RAG DEBUG", f"Knowledge Base ID: {KB_ID}\nQuery: {user}\nPassages Retrieved: {passages[:200]}..." if len(passages) > 200 else f"Knowledge Base ID: {KB_ID}\nPassages Retrieved: {passages}")
        
        prompt   = build_guardrail_prompt(passages, user)
        print_box("PROMPT DEBUG", f"Final prompt sent to Bedrock:\n{prompt[:300]}..." if len(prompt) > 300 else prompt)

        # assemble conversation in Bedrock's expected format with proper guardrail structure
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
                        "text": user,
                        "qualifiers": ["query"]
                    }
                }
            }
        ]
        
        convo_msgs = map_messages(history) + [{"role": "user", "content": user_content}]
        system_msgs = extract_system_messages(history)

        t0 = time.time()
        try:
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
            
            # Add system messages if any exist
            if system_msgs:
                converse_params["system"] = system_msgs
                
            # Call Bedrock directly and measure timing
            start_time = time.time()
            raw = bedrock.converse(**converse_params)
            end_time = time.time()
            
            # Calculate duration in milliseconds
            duration_ms = int((end_time - start_time) * 1000)
            
            # Track success and duration with LaunchDarkly
            tracker.track_success()
            tracker.track_duration(duration_ms)
            
            # For non-streaming responses, time to first token equals total time
            # since all tokens arrive together in one response
            tracker.track_time_to_first_token(duration_ms)
            
            # Extract and track token usage
            usage = raw.get("usage", {})
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)
            total_tokens = input_tokens + output_tokens
            
            if total_tokens > 0:
                # Track usage with TokenUsage object for LaunchDarkly
                token_usage = TokenUsage(total=total_tokens, input=input_tokens, output=output_tokens)
                tracker.track_tokens(token_usage)
            
            # Create a wrapped response object for compatibility
            reply_obj = {
                "output": raw["output"],
                "metrics": {
                    "latencyMs": duration_ms,
                    "tokens": {
                        "total": total_tokens,
                        "input": input_tokens,
                        "output": output_tokens
                    }
                }
            }
            
            # Calculate timing metrics
            total_latency = time.time() - t0
            
            # Debug: Show what metrics were tracked
            logging.info(f"LaunchDarkly AI tracked metrics: duration={duration_ms}ms, time_to_first_token={duration_ms}ms, tokens={total_tokens}, input={input_tokens}, output={output_tokens}")

            # trace object now lives at response["trace"]["guardrail"]
            g_trace = raw.get("trace", {}).get("guardrail", {})
            
            # Extract grounding and relevance scores from output assessments
            grounding = None
            relevance = None
            
            # Look in outputAssessments for contextual grounding scores
            output_assessments = g_trace.get("outputAssessments", {})
            
            if output_assessments:
                # Get the first (and usually only) guardrail assessment
                guardrail_id = list(output_assessments.keys())[0] if output_assessments else ""
                if guardrail_id and output_assessments.get(guardrail_id):
                    assessments = output_assessments[guardrail_id]
                    if isinstance(assessments, list) and len(assessments) > 0:
                        assessment = assessments[0]
                        # Look for contextual grounding scores in the correct structure
                        if "contextualGroundingPolicy" in assessment:
                            cg_policy = assessment["contextualGroundingPolicy"]
                            if "filters" in cg_policy:
                                for filter_item in cg_policy["filters"]:
                                    if filter_item.get("type") == "GROUNDING":
                                        grounding = filter_item.get("score")
                                    elif filter_item.get("type") == "RELEVANCE":  
                                        relevance = filter_item.get("score")
            
            # Extract contextual grounding metrics if available
            input_assessment = g_trace.get("inputAssessment", {})
            guardrail_id = list(input_assessment.keys())[0] if input_assessment else ""
            grounding_units = 0
            if guardrail_id and input_assessment.get(guardrail_id, {}).get("invocationMetrics", {}).get("usage", {}):
                grounding_units = input_assessment[guardrail_id]["invocationMetrics"]["usage"].get("contextualGroundingPolicyUnits", 0)
        except botocore.exceptions.ClientError as e:
            # Track error with LaunchDarkly
            tracker.track_error()
            logging.error("Bedrock error: %s", e)
            continue

        # Extract response text - handle LaunchDarkly response structure
        if "output" in reply_obj:
            reply_txt = reply_obj["output"]["message"]["content"][0]["text"]
        else:
            # Fallback: extract from raw response structure
            reply_txt = raw["output"]["message"]["content"][0]["text"]
            
        latency   = int((time.time() - t0)*1000)
        
        # Get token usage from our tracked metrics
        input_tokens = reply_obj.get("metrics", {}).get("tokens", {}).get("input", "?")
        output_tokens = reply_obj.get("metrics", {}).get("tokens", {}).get("output", "?")
        
        print_box("ASSISTANT", reply_txt)

        # ── feedback ──────────────────────────────────────────────────────────
        print_box("FEEDBACK", "👍  Was this helpful? (y/n)")
        fb = input("Your answer: ").strip().lower()
        if fb.startswith("y") and tracker:
            tracker.track_feedback({"kind": FeedbackKind.Positive})
        elif fb.startswith("n") and tracker:
            tracker.track_feedback({"kind": FeedbackKind.Negative})

        # ── accuracy metric for LaunchDarkly experiment ──────────────────────
        if grounding is not None:
            # Convert grounding score to percentage and send to LaunchDarkly
            accuracy_percentage = grounding * 100
            ld.track(
                "$ld:ai:hallucinations",
                context, 
                data=None,
                metric_value=accuracy_percentage
            )
            logging.info(f"Sent accuracy metric to LaunchDarkly: {accuracy_percentage:.1f}%")
            
        # ── relevance metric for LaunchDarkly experiment ───────────────────────
        if relevance is not None:
            # Convert relevance score to percentage and send to LaunchDarkly
            relevance_percentage = relevance * 100
            ld.track(
                "$ld:ai:relevance",
                context, 
                data=None,
                metric_value=relevance_percentage
            )
            logging.info(f"Sent relevance metric to LaunchDarkly: {relevance_percentage:.1f}%")

        # ── session summary ──────────────────────────────────────────────────
        met = reply_obj.get("metrics", {})
        accuracy_str = f"{grounding:.2f}" if grounding is not None else "None"
        relevance_str = f"{relevance:.2f}" if relevance is not None else "None"
        summary = (
            f"Latency: {latency} ms | Bedrock tokens in/out: "
            f"{input_tokens}/{output_tokens} | "
            f"Accuracy: {accuracy_str} | Relevance: {relevance_str}"
        )
        print_box("METRICS", summary)

        # update local history for context
        history.append(SimpleMessage(role="user", content=user))
        history.append(SimpleMessage(role="assistant", content=reply_txt))

        ld.flush()  # push events quickly

    ld.close()
    print("✓  Finished. Goodbye!")

if __name__ == "__main__":
    main()