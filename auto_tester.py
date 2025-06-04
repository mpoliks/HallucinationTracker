#!/usr/bin/env python3
"""
auto_tester.py - Automated testing script for HallucinationTracker

Continuously runs the chat bot with random questions from the evaluation dataset,
provides simulated positive feedback (90%+ satisfaction rate), and handles
AWS token expiration gracefully.
"""

import os
import sys
import json
import time
import random
import logging
import subprocess
import signal
from pathlib import Path
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    handlers=[
        logging.FileHandler("auto_tester.log"),
        logging.StreamHandler()
    ]
)

class AutoTester:
    def __init__(self, dataset_path: str = "samples/togglebank_eval_dataset_bedrock.jsonl"):
        self.dataset_path = dataset_path
        self.questions = self.load_questions()
        self.target_positive_rate = 0.95  # Target 95% positive feedback
        self.session_count = 0
        self.total_questions = 0
        self.positive_feedback_given = 0
        self.running = True
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def load_questions(self) -> List[str]:
        """Load questions from the JSONL evaluation dataset"""
        questions = []
        try:
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            
                            # Handle both formats: simple and bedrock
                            if 'prompt' in data:
                                # Simple format: {"prompt": "question", ...}
                                questions.append(data['prompt'])
                            elif 'conversationTurns' in data:
                                # Bedrock format: {"conversationTurns": [{"prompt": {"content": [{"text": "question"}]}}]}
                                turns = data.get('conversationTurns', [])
                                for turn in turns:
                                    prompt_data = turn.get('prompt', {})
                                    content_list = prompt_data.get('content', [])
                                    for content in content_list:
                                        if 'text' in content:
                                            questions.append(content['text'])
                                            
                        except json.JSONDecodeError as e:
                            logging.warning(f"Skipping malformed line: {line[:50]}...")
                            continue
            
            logging.info(f"Loaded {len(questions)} questions from dataset")
            return questions
            
        except FileNotFoundError:
            logging.error(f"Dataset file not found: {self.dataset_path}")
            # Fallback questions if dataset not found
            return [
                "What are the different account tiers and how do I qualify?",
                "What fees are waived for Gold tier customers?",
                "How do I enable two-factor authentication?",
                "What should I do if my debit card is lost or stolen?",
                "How do I request a credit limit increase?"
            ]
    
    def get_random_question(self) -> str:
        """Get a random question from the dataset"""
        return random.choice(self.questions)
    
    def should_give_positive_feedback(self) -> bool:
        """
        Determine if we should give positive feedback
        Uses dynamic adjustment to maintain ~95% positive rate
        """
        if self.total_questions == 0:
            # First question, use target rate
            return random.random() < self.target_positive_rate
        
        # Calculate current positive rate
        current_rate = self.positive_feedback_given / self.total_questions
        
        # Adjust probability based on how far we are from target
        adjustment = (self.target_positive_rate - current_rate) * 0.5  # Gentle adjustment
        adjusted_rate = self.target_positive_rate + adjustment
        
        # Keep within reasonable bounds
        adjusted_rate = max(0.8, min(1.0, adjusted_rate))
        
        return random.random() < adjusted_rate
    
    def run_chat_session(self) -> bool:
        """
        Run a single chat session with the bot
        Returns True if successful, False if AWS token expired
        """
        try:
            # Start the chat bot process
            process = subprocess.Popen(
                [sys.executable, "script.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Get a random question
            question = self.get_random_question()
            logging.info(f"Session {self.session_count + 1}: Asking: {question}")
            
            # Prepare the full interaction: question + feedback + exit
            feedback = "y" if self.should_give_positive_feedback() else "n"
            feedback_text = "positive" if feedback == "y" else "negative"
            
            # Calculate current stats for logging
            temp_positive = self.positive_feedback_given + (1 if feedback == "y" else 0)
            temp_total = self.total_questions + 1
            current_rate = (temp_positive / temp_total) * 100
            
            # Send the complete interaction
            input_sequence = f"{question}\n{feedback}\nexit\n"
            
            try:
                # Run the complete interaction with timeout
                stdout, stderr = process.communicate(input=input_sequence, timeout=30)
                
                # Check for errors
                if "ExpiredTokenException" in stderr or "expired" in stderr.lower():
                    logging.error("AWS tokens expired. Please refresh your credentials.")
                    return False
                elif "Missing" in stderr and "LaunchDarkly" in stderr:
                    logging.error("LaunchDarkly configuration issue. Check your AI config.")
                    return False
                elif process.returncode != 0 and stderr:
                    logging.warning(f"Process error: {stderr[:200]}...")
                
                # Extract assistant response from stdout
                self.extract_and_log_response(stdout)
                
                logging.info(f"Providing {feedback_text} feedback (running rate: {current_rate:.1f}%)")
                
                self.total_questions += 1
                if feedback == "y":
                    self.positive_feedback_given += 1
                logging.info(f"Session {self.session_count + 1} completed successfully")
                logging.info(f"✅ New user context created for next session")
                return True
                
            except subprocess.TimeoutExpired:
                logging.warning("Session timed out, terminating...")
                process.kill()
                return True
                
        except Exception as e:
            logging.error(f"Error in chat session: {e}")
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=2)
            except:
                pass
            return True  # Continue trying unless it's a token issue
    
    def extract_and_log_response(self, output: str):
        """Extract and log the assistant's response from the chat output"""
        try:
            lines = output.split('\n')
            in_assistant_box = False
            assistant_response = []
            
            for line in lines:
                # Look for the ASSISTANT box header
                if "ASSISTANT" in line and "│" in line:
                    in_assistant_box = True
                    continue
                # Look for the end of the box
                elif line.strip().startswith("└") and in_assistant_box:
                    break
                # Collect lines inside the assistant box
                elif in_assistant_box and line.startswith("│"):
                    # Remove the box formatting
                    clean_line = line[2:].rstrip() if len(line) > 2 else ""
                    if clean_line:
                        assistant_response.append(clean_line)
            
            if assistant_response:
                response_text = " ".join(assistant_response).strip()
                if response_text:
                    # Truncate long responses for cleaner logging
                    if len(response_text) > 300:
                        response_text = response_text[:300] + "..."
                    logging.info(f"🤖 Bot Response: {response_text}")
                else:
                    logging.info("🤖 Bot Response: [Empty response]")
            else:
                logging.info("🤖 Bot Response: [Could not parse response]")
                
        except Exception as e:
            logging.info(f"🤖 Bot Response: [Error parsing: {e}]")
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        logging.info("\nReceived interrupt signal. Shutting down gracefully...")
        self.running = False
    
    def run(self):
        """Main execution loop"""
        logging.info("🚀 Starting HallucinationTracker Auto Tester")
        logging.info(f"📊 Dataset: {len(self.questions)} questions loaded")
        logging.info(f"😊 Target positive rate: {self.target_positive_rate*100:.0f}%")
        logging.info("🔄 Running sessions every 10 seconds...")
        logging.info("Press Ctrl+C to stop")
        
        while self.running:
            try:
                self.session_count += 1
                
                logging.info(f"\n{'='*60}")
                logging.info(f"Starting session {self.session_count}")
                
                # Run a chat session
                success = self.run_chat_session()
                
                if not success:
                    logging.error("❌ AWS token expired or critical error. Stopping auto tester.")
                    logging.info("💡 Please refresh your AWS credentials and restart.")
                    break
                
                if not self.running:
                    break
                
                # Wait 10 seconds before next session
                logging.info(f"✅ Session {self.session_count} complete. Waiting 10 seconds...")
                for i in range(10):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                time.sleep(5)  # Brief pause before retrying
        
        # Final summary
        logging.info(f"\n{'='*60}")
        logging.info("📋 AUTO TESTER SUMMARY")
        logging.info(f"Sessions completed: {self.session_count}")
        logging.info(f"Questions asked: {self.total_questions}")
        logging.info(f"Positive feedback given: {self.positive_feedback_given}")
        if self.total_questions > 0:
            actual_rate = (self.positive_feedback_given / self.total_questions) * 100
            logging.info(f"Actual positive rate: {actual_rate:.1f}% (target: {self.target_positive_rate*100:.0f}%)")
        logging.info(f"Average questions per session: {self.total_questions/max(self.session_count,1):.1f}")
        logging.info("👋 Auto tester stopped.")

def main():
    """Main entry point"""
    # Check if we're in the right directory
    if not Path("script.py").exists():
        print("❌ Error: script.py not found in current directory")
        print("💡 Please run this from the HallucinationTracker directory")
        sys.exit(1)
    
    # Check if dataset exists
    dataset_path = "samples/togglebank_eval_dataset_bedrock.jsonl"
    if not Path(dataset_path).exists():
        print(f"⚠️  Warning: Dataset not found at {dataset_path}")
        print("🔄 Will use fallback questions")
    
    # Run the auto tester
    tester = AutoTester(dataset_path)
    tester.run()

if __name__ == "__main__":
    main() 