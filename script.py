#!/usr/bin/env python3
"""
chat_rag_guardrail.py – Terminal chat bot with:
  • LaunchDarkly AI Configs           – prompt/model governance
  • S3-backed RAG retrieval           – reference source
  • Bedrock inline guardrail          – hallucination & relevance check
  • Live metrics & user feedback      – sent back to LaunchDarkly

Keys come from .env in the same folder.
"""
import os, sys, json, signal, hashlib, logging, textwrap, time, uuid, random
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

def get_kb_passages(question: str, kb_id: str) -> str:
    """
    Query AWS Bedrock Knowledge Base using vector search
    """
    try:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': question
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 25  # Expanded window for better accuracy
                }
            }
        )
        
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
    return f"Source Information:\n{passages}\n\nCustomer Question: {question}"

# Simple Message class to match expected structure
class SimpleMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
    
    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content
        }

# graceful Ctrl-C
signal.signal(signal.SIGINT, lambda *_: sys.exit("\n👋  bye!"))

def check_factual_accuracy(source_passages: str, response_text: str, generator_model_id: str, custom_params: dict) -> float:
    """
    Check factual accuracy by extracting and comparing key facts
    Returns a score from 0.0 to 1.0 representing factual accuracy
    
    Uses a dedicated fact-checking model from LaunchDarkly AI Config for independent evaluation
    """
    
    # Get LLM-as-judge model from LaunchDarkly AI Config custom parameters
    fact_checker_model = custom_params.get('llm_as_judge', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
    
    # Log which models are being used for transparency
    logging.info(f"Generator model: {generator_model_id}, LLM-as-judge model: {fact_checker_model}")
    
    fact_check_prompt = f"""
You are a fact-checking expert. Compare the response against the source material and identify any factual errors.

SOURCE MATERIAL:
{source_passages}

RESPONSE TO CHECK:
{response_text}

Instructions:
1. Extract key factual claims from the response (names, numbers, dates, policies, requirements)
2. Check each factual claim against the source material
3. Ignore tone, style, helpfulness - focus ONLY on factual accuracy
4. Return a JSON with:
   - "factual_claims": list of key facts claimed in response
   - "accurate_claims": list of claims that are accurate per source
   - "inaccurate_claims": list of claims that are wrong or unsupported
   - "accuracy_score": decimal from 0.0 to 1.0

Response format: {{"factual_claims": [...], "accurate_claims": [...], "inaccurate_claims": [...], "accuracy_score": 0.95}}
"""

    try:
        fact_check_response = bedrock.converse(
            modelId=fact_checker_model,  # Use LLM-as-judge from LaunchDarkly config
            messages=[
                {
                    "role": "user", 
                    "content": [{"text": fact_check_prompt}]
                }
            ]
        )
        
        fact_result = fact_check_response["output"]["message"]["content"][0]["text"]
        
        # Parse JSON response
        import json
        try:
            fact_data = json.loads(fact_result)
            return fact_data.get("accuracy_score", 0.0)
        except json.JSONDecodeError:
            # Fallback: try to extract score from text
            if "accuracy_score" in fact_result:
                import re
                score_match = re.search(r'"accuracy_score":\s*([0-9.]+)', fact_result)
                if score_match:
                    return float(score_match.group(1))
            return 0.0
            
    except Exception as e:
        logging.error(f"Factual accuracy check failed: {e}")
        return 0.0

# ── main loop ────────────────────────────────────────────────────────────────
def main() -> None:
    # Generate unique user for fresh experiment exposure each time
    unique_user_key = f"user-{uuid.uuid4().hex[:8]}"
    context = Context.builder(unique_user_key).kind("user").name(f"CLI Tester {unique_user_key}").build()
    
    # Default config - will be overridden by LaunchDarkly AI configs
    default_cfg = AIConfig(
        enabled=True, 
        model=ModelConfig(name="us.anthropic.claude-3-5-sonnet-20241022-v2:0"), 
        messages=[]
    )

    cfg, tracker = ai_client.config(LD_KEY, context, default_cfg, {})
    
    # Debug what LaunchDarkly actually returned vs our defaults
    logging.info(f"=== AI CONFIG DEBUG ===")
    logging.info(f"Our default model: {default_cfg.model.name}")
    logging.info(f"Our default messages count: {len(default_cfg.messages)}")
    logging.info(f"LaunchDarkly returned model: {cfg.model.name if cfg.model else 'None'}")
    logging.info(f"LaunchDarkly returned messages count: {len(cfg.messages) if cfg.messages else 0}")
    logging.info(f"Final model being used: {cfg.model.name if cfg.model else 'fallback'}")
    logging.info(f"=== END DEBUG ===")
    
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
    
    # Debug LLM-as-judge configuration
    llm_as_judge = custom_params.get('llm_as_judge', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
    eval_freq = float(custom_params.get('eval_freq', '1.0'))  # Default to 100% evaluation
    logging.info(f"LLM-as-judge model: {llm_as_judge}")
    logging.info(f"Evaluation frequency: {eval_freq*100:.1f}%")
    
    model_id = cfg.model.name if cfg.model else "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    history  = list(cfg.messages) if cfg.messages else []   # seed messages from LD

    logging.info(f"Generated unique user: {unique_user_key}")
    print_box("READY", f"User: {unique_user_key}\nMLOps model: {model_id}\nGuardrail: {GR_ID}@v{GR_VER}\nKnowledge Base: {KB_ID}\nType 'exit' to quit.")

    while True:
        user = input("\n🧑  You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break

        passages = get_kb_passages(user, KB_ID)
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

        # Debug: Show what system messages are being sent to Bedrock
        logging.info(f"=== SYSTEM MESSAGES DEBUG ===")
        logging.info(f"Number of system messages: {len(system_msgs)}")
        for i, msg in enumerate(system_msgs):
            logging.info(f"System message {i+1}: {msg['text'][:200]}..." if len(msg['text']) > 200 else f"System message {i+1}: {msg['text']}")
        logging.info(f"=== END SYSTEM DEBUG ===")

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
            
            # Debug guardrail assessment details
            logging.info(f"=== GUARDRAIL DEBUG ===")
            logging.info(f"Full guardrail trace keys: {list(g_trace.keys()) if g_trace else 'None'}")
            output_assessments = g_trace.get("outputAssessments", {})
            if output_assessments:
                logging.info(f"Output assessments found for: {list(output_assessments.keys())}")
                for guardrail_id, assessments in output_assessments.items():
                    if isinstance(assessments, list) and len(assessments) > 0:
                        assessment = assessments[0]
                        logging.info(f"Assessment keys: {list(assessment.keys())}")
                        if "contextualGroundingPolicy" in assessment:
                            cg_policy = assessment["contextualGroundingPolicy"]
                            logging.info(f"Contextual grounding policy: {cg_policy}")
            logging.info(f"=== END GUARDRAIL DEBUG ===")
            
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

        # ── factual accuracy check ────────────────────────────────────────────
        # Use eval_freq to control how often we run the expensive accuracy check
        factual_accuracy = None
        random_value = random.random()
        should_evaluate = random_value < eval_freq
        
        if should_evaluate:
            factual_accuracy = check_factual_accuracy(passages, reply_txt, model_id, custom_params)
            logging.info(f"Accuracy score: {factual_accuracy:.3f}")
        else:
            logging.info(f"Accuracy check skipped (random={random_value:.3f} >= eval_freq={eval_freq:.1f}) - cost savings mode")

        # ── feedback ──────────────────────────────────────────────────────────
        print_box("FEEDBACK", "👍  Was this helpful? (y/n)")
        fb = input("Your answer: ").strip().lower()
        if fb.startswith("y") and tracker:
            tracker.track_feedback({"kind": FeedbackKind.Positive})
        elif fb.startswith("n") and tracker:
            tracker.track_feedback({"kind": FeedbackKind.Negative})

        # ── accuracy metric for LaunchDarkly experiment ──────────────────────
        if grounding is not None:
            # Convert grounding score to percentage and send to LaunchDarkly as Source Fidelity
            grounding_percentage = grounding * 100
            ld.track(
                "$ld:ai:source-fidelity",
                context, 
                data=None,
                metric_value=grounding_percentage
            )
            logging.info(f"Sent source fidelity metric to LaunchDarkly: {grounding_percentage:.1f}%")
            
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

        # ── accuracy metric for LaunchDarkly (factual accuracy = anti-hallucination) ───────────────────
        if factual_accuracy is not None:
            factual_accuracy_percentage = factual_accuracy * 100
            ld.track(
                "$ld:ai:hallucinations",
                context,
                data=None,
                metric_value=factual_accuracy_percentage
            )
            logging.info(f"Sent accuracy metric to LaunchDarkly: {factual_accuracy_percentage:.1f}%")
        else:
            logging.info(f"Accuracy metric not sent to LaunchDarkly (check skipped for cost savings)")

        # ── session summary ──────────────────────────────────────────────────
        met = reply_obj.get("metrics", {})
        grounding_str = f"{grounding:.2f}" if grounding is not None else "None"
        relevance_str = f"{relevance:.2f}" if relevance is not None else "None"
        accuracy_str = f"{factual_accuracy:.2f}" if factual_accuracy is not None else "SKIPPED"
        summary = (
            f"Latency: {latency} ms | Bedrock tokens in/out: "
            f"{input_tokens}/{output_tokens} | "
            f"Source Fidelity: {grounding_str} | Relevance: {relevance_str} | "
            f"Accuracy: {accuracy_str}"
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