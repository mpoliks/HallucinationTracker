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
    def __init__(self, dataset_path: str = "/Users/marek/Downloads/togglebank_eval_dataset.jsonl"):
        self.dataset_path = dataset_path
        self.questions = self.load_questions()
        self.positive_feedback_rate = 0.90  # 90% positive feedback
        self.session_count = 0
        self.total_questions = 0
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
                        # Handle the malformed first line
                        if line.startswith(' fr{"prompt"'):
                            line = line[3:]  # Remove ' fr' prefix
                        
                        try:
                            data = json.loads(line)
                            if 'prompt' in data:
                                questions.append(data['prompt'])
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
        """Determine if we should give positive feedback (90% rate)"""
        return random.random() < self.positive_feedback_rate
    
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
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait a moment for the bot to initialize
            time.sleep(2)
            
            # Check if process is still running (initialization success)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                if "ExpiredTokenException" in stderr or "expired" in stderr.lower():
                    logging.error("AWS tokens expired. Please refresh your credentials.")
                    return False
                elif "Missing" in stderr and "LaunchDarkly" in stderr:
                    logging.error("LaunchDarkly configuration issue. Check your AI config.")
                    return False
                else:
                    logging.error(f"Bot failed to start: {stderr}")
                    return False
            
            # Get a random question
            question = self.get_random_question()
            logging.info(f"Session {self.session_count + 1}: Asking: {question}")
            
            # Send the question
            process.stdin.write(f"{question}\n")
            process.stdin.flush()
            
            # Wait for response (give it time to process)
            time.sleep(8)
            
            # Check if process died during processing
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                if "ExpiredTokenException" in stderr or "expired" in stderr.lower():
                    logging.error("AWS tokens expired during processing.")
                    return False
                else:
                    logging.warning(f"Process died during processing: {stderr}")
                    return True  # Continue trying
            
            # Provide feedback
            feedback = "y" if self.should_give_positive_feedback() else "n"
            feedback_text = "positive" if feedback == "y" else "negative"
            logging.info(f"Providing {feedback_text} feedback")
            
            process.stdin.write(f"{feedback}\n")
            process.stdin.flush()
            
            # Wait a moment then exit the chat
            time.sleep(2)
            process.stdin.write("exit\n")
            process.stdin.flush()
            
            # Wait for clean exit
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.warning("Process didn't exit cleanly, terminating...")
                process.terminate()
                process.wait(timeout=2)
            
            self.total_questions += 1
            logging.info(f"Session {self.session_count + 1} completed successfully")
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
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        logging.info("\nReceived interrupt signal. Shutting down gracefully...")
        self.running = False
    
    def run(self):
        """Main execution loop"""
        logging.info("🚀 Starting HallucinationTracker Auto Tester")
        logging.info(f"📊 Dataset: {len(self.questions)} questions loaded")
        logging.info(f"😊 Positive feedback rate: {self.positive_feedback_rate*100:.0f}%")
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
    dataset_path = "/Users/marek/Downloads/togglebank_eval_dataset.jsonl"
    if not Path(dataset_path).exists():
        print(f"⚠️  Warning: Dataset not found at {dataset_path}")
        print("🔄 Will use fallback questions")
    
    # Run the auto tester
    tester = AutoTester(dataset_path)
    tester.run()

if __name__ == "__main__":
    main() 