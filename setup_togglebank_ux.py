#!/usr/bin/env python3
"""
Setup script for ToggleBank UX with Python chatbot backend
"""
import subprocess
import sys
import os

def run_command(command, cwd=None):
    """Run a command and print output"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    return result.returncode == 0

def main():
    print("🚀 Setting up ToggleBank UX with Python Chatbot Backend")
    print("=" * 60)
    
    # 1. Install Python dependencies
    print("\n1. Installing Python dependencies...")
    if not run_command("pip install -r requirements.txt"):
        print("❌ Failed to install Python dependencies")
        return
    print("✅ Python dependencies installed")
    
    # 2. Install Node.js dependencies for frontend
    print("\n2. Installing Node.js dependencies...")
    if not run_command("npm install"):
        print("❌ Failed to install Node.js dependencies")
        print("   Make sure you have Node.js installed: https://nodejs.org/")
        return
    print("✅ Node.js dependencies installed")
    
    # 3. Check for .env file
    print("\n3. Checking environment configuration...")
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        print("   Please create a .env file with your credentials:")
        print("   - LAUNCHDARKLY_SDK_KEY=...")
        print("   - LAUNCHDARKLY_AI_CONFIG_KEY=...")
        print("   - LAUNCHDARKLY_LLM_JUDGE_KEY=...")
        print("   - AWS_REGION=...")
        print("   - AWS credentials (or use AWS SSO)")
        return
    print("✅ .env file found")
    
    # 4. Create frontend .env.local
    print("\n4. Creating frontend environment file...")
    frontend_env = """# ToggleBank Frontend Environment
PYTHON_API_URL=http://localhost:8000
LD_SDK_KEY=your_launchdarkly_sdk_key
"""
    with open(".env.local", "w") as f:
        f.write(frontend_env)
    print("✅ Created .env.local for frontend")
    
    print("\n🎉 Setup complete!")
    print("\n" + "=" * 60)
    print("HOW TO RUN:")
    print("=" * 60)
    
    print("\n1. Start the Python backend (Terminal 1):")
    print("   python fastapi_wrapper.py")
    print("   → Runs on http://localhost:8000")
    
    print("\n2. Start the ToggleBank frontend (Terminal 2):")
    print("   npm run dev")
    print("   → Runs on http://localhost:3000")
    
    print("\n3. Open your browser to http://localhost:3000")
    print("   → Click the floating chat icon (bottom right)")
    print("   → Enjoy your ToggleBank-branded chatbot! 🤖")
    
    print("\n" + "=" * 60)
    print("FEATURES:")
    print("✅ Exact ToggleBank UI/UX")
    print("✅ Your Python RAG + Guardrail + LLM-judge logic")
    print("✅ LaunchDarkly AI configs integration")
    print("✅ Feedback tracking (thumbs up/down)")
    print("✅ Responsive design (mobile + desktop)")
    print("✅ Real-time chat interface")

if __name__ == "__main__":
    main() 