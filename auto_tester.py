#!/usr/bin/env python3
"""
Auto Tester for HallucinationTracker Chat Bot
Runs automated sessions with random questions and feedback
"""
import json
import logging
import random
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

class HallucinationTrackerAutoTester:
    def __init__(self):
        self.dataset_path = "samples/togglebank_eval_dataset_bedrock.jsonl"
        self.questions = []
        self.session_count = 0
        self.total_questions = 0
        self.positive_feedback_given = 0
        self.target_positive_rate = 0.95  # 95%
        self.session_interval = 10  # seconds
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)-7s | %(message)s',
            handlers=[
                logging.FileHandler('auto_tester.log'),
                logging.StreamHandler()
            ]
        )
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        
    def load_dataset(self):
        """Load questions from the evaluation dataset"""
        try:
            with open(self.dataset_path, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    # Handle both simple and bedrock formats
                    if 'conversationTurns' in data:
                        # Bedrock format
                        for turn in data['conversationTurns']:
                            if 'prompt' in turn:
                                content_list = turn['prompt'].get('content', [])
                                for content in content_list:
                                    if 'text' in content:
                                        self.questions.append(content['text'])
                    else:
                        # Simple format
                        if 'question' in data:
                            self.questions.append(data['question'])
                        elif 'user' in data:
                            self.questions.append(data['user'])
            
            logging.info(f"Loaded {len(self.questions)} questions from dataset")
            
        except FileNotFoundError:
            logging.error(f"Dataset file not found: {self.dataset_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing dataset: {e}")
            sys.exit(1)
    
    def get_random_question(self) -> str:
        """Get a random question from the dataset"""
        return random.choice(self.questions)
    
    def should_give_positive_feedback(self) -> bool:
        """
        Dynamically adjust feedback to maintain ~95% positive rate
        """
        if self.total_questions == 0:
            return True  # Start with positive
        
        current_rate = self.positive_feedback_given / self.total_questions
        
        # If we're below target, increase positive probability
        # If we're above target, decrease positive probability
        adjusted_rate = self.target_positive_rate + (self.target_positive_rate - current_rate) * 0.5
        adjusted_rate = max(0.1, min(0.99, adjusted_rate))  # Keep between 10% and 99%
        
        return random.random() < adjusted_rate
    
    def run_chat_session(self) -> bool:
        """
        Run a single chat session with the bot using direct process interaction
        Returns True if successful, False if AWS token expired
        """
        try:
            # Start the chat bot process
            process = subprocess.Popen(
                [sys.executable, "script.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                text=True,
                bufsize=0  # Unbuffered
            )
            
            # Get a random question
            question = self.get_random_question()
            logging.info(f"Session {self.session_count + 1}: Asking: {question}")
            
            # Send the question
            process.stdin.write(question + '\n')
            process.stdin.flush()
            
            # Read output until we get to feedback prompt
            start_time = time.time()
            timeout = 60  # 60 second timeout
            
            # Buffer to collect all output
            full_output = ""
            
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    # Process ended, read any remaining output
                    remaining_output = process.stdout.read()
                    if remaining_output:
                        full_output += remaining_output
                    break
                
                try:
                    # Read available characters
                    char = process.stdout.read(1)
                    if not char:
                        time.sleep(0.1)
                        continue
                    
                    full_output += char
                    
                    # Check if we've reached the feedback prompt
                    if "Was this helpful? (y/n)" in full_output:
                        # We found the feedback prompt, break to provide feedback
                        break
                
                except Exception as e:
                    logging.warning(f"Error reading output: {e}")
                    break
            
            # Extract assistant response from the full output
            assistant_response_text = self.extract_assistant_response(full_output)
            if assistant_response_text:
                # Truncate long responses for cleaner logging
                if len(assistant_response_text) > 300:
                    assistant_response_text = assistant_response_text[:300] + "..."
                logging.info(f"🤖 Bot Response: {assistant_response_text}")
            else:
                logging.info("🤖 Bot Response: [Could not capture response]")
            
            # Provide feedback
            feedback = "y" if self.should_give_positive_feedback() else "n"
            feedback_text = "positive" if feedback == "y" else "negative"
            
            # Calculate current stats for logging
            temp_positive = self.positive_feedback_given + (1 if feedback == "y" else 0)
            temp_total = self.total_questions + 1
            current_rate = (temp_positive / temp_total) * 100
            
            logging.info(f"Providing {feedback_text} feedback (running rate: {current_rate:.1f}%)")
            
            # Send feedback
            process.stdin.write(feedback + '\n')
            process.stdin.flush()
            
            # Wait a moment then exit
            time.sleep(2)
            process.stdin.write('exit\n')
            process.stdin.flush()
            
            # Wait for process to finish
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            # Update stats
            self.total_questions += 1
            if feedback == "y":
                self.positive_feedback_given += 1
            
            logging.info(f"Session {self.session_count + 1} completed successfully")
            logging.info(f"✅ New user context created for next session")
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
    
    def extract_assistant_response(self, output: str) -> str:
        """Extract the assistant response from the chat output"""
        try:
            lines = output.split('\n')
            in_assistant_box = False
            assistant_response_lines = []
            
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
                    # Remove the box formatting (│ and any leading spaces)
                    clean_line = line[1:].strip() if len(line) > 1 else ""
                    # Skip lines that are just box formatting (dashes, etc.)
                    if clean_line and not clean_line.startswith("─") and clean_line != "│":
                        assistant_response_lines.append(clean_line)
            
            if assistant_response_lines:
                # Join the lines and clean up any remaining formatting artifacts
                response_text = " ".join(assistant_response_lines).strip()
                # Remove any remaining │ characters that might have been missed
                response_text = response_text.replace("│", "").strip()
                # Clean up multiple spaces
                response_text = " ".join(response_text.split())
                return response_text
            
            return ""
            
        except Exception as e:
            logging.warning(f"Error extracting response: {e}")
            return ""
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        logging.info("\n🛑 Received shutdown signal...")
        self.print_final_stats()
        sys.exit(0)
    
    def print_final_stats(self):
        """Print final statistics"""
        if self.total_questions > 0:
            final_rate = (self.positive_feedback_given / self.total_questions) * 100
            logging.info("=" * 60)
            logging.info(f"📊 FINAL STATISTICS:")
            logging.info(f"   Sessions completed: {self.session_count}")
            logging.info(f"   Total questions: {self.total_questions}")
            logging.info(f"   Positive feedback: {self.positive_feedback_given}")
            logging.info(f"   Final positive rate: {final_rate:.1f}%")
            logging.info(f"   Target rate: {self.target_positive_rate * 100:.1f}%")
            logging.info("=" * 60)
    
    def run(self):
        """Main execution loop"""
        self.load_dataset()
        
        logging.info("🚀 Starting HallucinationTracker Auto Tester")
        logging.info(f"📊 Dataset: {len(self.questions)} questions loaded")
        logging.info(f"😊 Target positive rate: {self.target_positive_rate * 100:.0f}%")
        logging.info(f"🔄 Running sessions every {self.session_interval} seconds...")
        logging.info("Press Ctrl+C to stop")
        
        try:
            while True:
                logging.info("\n" + "=" * 60)
                logging.info(f"Starting session {self.session_count + 1}")
                
                success = self.run_chat_session()
                
                if not success:
                    logging.error("Failed to run session - stopping auto tester")
                    break
                
                self.session_count += 1
                logging.info(f"✅ Session {self.session_count} complete. Waiting {self.session_interval} seconds...")
                
                time.sleep(self.session_interval)
                
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)
        finally:
            self.print_final_stats()

if __name__ == "__main__":
    tester = HallucinationTrackerAutoTester()
    tester.run() 