#!/usr/bin/env python3
"""
Test script for guardrail clamp functionality

This script tests the automatic flag disabling feature by:
1. Checking current guardrail status
2. Testing manual flag disable/enable
3. Monitoring the metrics
"""

import requests
import json
import time
import os
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_guardrail_status():
    """Test getting guardrail status"""
    print("📊 Testing Guardrail Status...")
    url = f"{BASE_URL}/api/guardrail/status"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Status Retrieved:")
        print(f"   Flag Enabled: {data.get('flag_enabled', 'unknown')}")
        print(f"   Flag Key: {data.get('flag_key', 'unknown')}")
        print(f"   Environment: {data.get('environment', 'unknown')}")
        print(f"   API Client Enabled: {data.get('api_client_enabled', 'unknown')}")
        
        monitoring = data.get('monitoring', {})
        if monitoring.get('total_requests'):
            print(f"   Recent Requests: {monitoring['total_requests']}")
            print(f"   Error Rate: {monitoring.get('error_rate', 0):.1%}")
            if monitoring.get('avg_accuracy'):
                print(f"   Avg Accuracy: {monitoring['avg_accuracy']:.3f}")
            if monitoring.get('avg_grounding'):
                print(f"   Avg Grounding: {monitoring['avg_grounding']:.3f}")
        else:
            print("   No recent monitoring data")
            
        return data
        
    except requests.RequestException as e:
        print(f"❌ Failed to get status: {e}")
        return None

def test_manual_disable():
    """Test manually disabling the flag"""
    print("\n🛑 Testing Manual Flag Disable...")
    url = f"{BASE_URL}/api/guardrail/manual-disable"
    
    try:
        response = requests.post(url, params={"disable_reason": "Testing guardrail clamp system"})
        response.raise_for_status()
        data = response.json()
        
        if data.get('success'):
            print(f"✅ Flag Disabled: {data.get('message')}")
            print(f"   Flag Version: {data.get('flag_version')}")
        else:
            print(f"❌ Failed to disable: {data}")
            
        return data
        
    except requests.RequestException as e:
        print(f"❌ Failed to disable flag: {e}")
        return None

def test_recovery():
    """Test recovering from guardrail"""
    print("\n🔄 Testing Guardrail Recovery...")
    url = f"{BASE_URL}/api/guardrail/recovery"
    
    try:
        response = requests.post(url, params={"recovery_reason": "Testing complete - re-enabling flag"})
        response.raise_for_status()
        data = response.json()
        
        if data.get('success'):
            print(f"✅ Flag Re-enabled: {data.get('message')}")
            print(f"   Flag Version: {data.get('flag_version')}")
        else:
            print(f"❌ Failed to recover: {data}")
            
        return data
        
    except requests.RequestException as e:
        print(f"❌ Failed to recover flag: {e}")
        return None

def test_reset_cooldowns():
    """Test resetting cooldown timers"""
    print("\n⏰ Testing Cooldown Reset...")
    url = f"{BASE_URL}/api/guardrail/reset-cooldowns"
    
    try:
        response = requests.post(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get('success'):
            print(f"✅ Cooldowns Reset: {data.get('message')}")
            print(f"   Demo Mode: {data.get('demo_mode')}")
            print(f"   Trigger Cooldown: {data.get('cooldown_minutes')} minutes")
            print(f"   Disable Cooldown: {data.get('disable_cooldown_minutes')} minutes")
        else:
            print(f"❌ Failed to reset cooldowns: {data}")
            
        return data
        
    except requests.RequestException as e:
        print(f"❌ Failed to reset cooldowns: {e}")
        return None

def test_metrics():
    """Test getting guardrail metrics"""
    print("\n📈 Testing Metrics Endpoint...")
    url = f"{BASE_URL}/api/guardrail/metrics"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        metrics = data.get('metrics', [])
        summary = data.get('summary', {})
        thresholds = data.get('thresholds', {})
        
        print(f"✅ Metrics Retrieved:")
        print(f"   Total Metrics: {len(metrics)}")
        print(f"   Window Minutes: {summary.get('window_minutes', 'unknown')}")
        
        if thresholds:
            print(f"   Thresholds:")
            print(f"     Accuracy Critical: {thresholds.get('min_accuracy_critical', 'unknown')}")
            print(f"     Accuracy Warning: {thresholds.get('min_accuracy_warning', 'unknown')}")
            print(f"     Grounding Critical: {thresholds.get('min_grounding_critical', 'unknown')}")
            print(f"     Grounding Warning: {thresholds.get('min_grounding_warning', 'unknown')}")
        
        if metrics:
            latest = metrics[-1]
            print(f"   Latest Metric:")
            print(f"     Timestamp: {latest.get('timestamp', 'unknown')}")
            print(f"     Accuracy: {latest.get('accuracy_score', 'N/A')}")
            print(f"     Grounding: {latest.get('grounding_score', 'N/A')}")
            print(f"     Error: {latest.get('error_occurred', 'N/A')}")
        
        return data
        
    except requests.RequestException as e:
        print(f"❌ Failed to get metrics: {e}")
        return None

def test_chat_to_generate_metrics():
    """Send a test chat to generate some metrics"""
    print("\n💬 Sending Test Chat to Generate Metrics...")
    url = f"{BASE_URL}/api/chat"
    
    payload = {
        "aiConfigKey": "toggle-bank-rag",
        "userInput": "What are my current account balances?"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Chat Response Received:")
        print(f"   Request ID: {data.get('requestId', 'unknown')}")
        print(f"   Enabled: {data.get('enabled', 'unknown')}")
        print(f"   Pending Metrics: {data.get('pendingMetrics', 'unknown')}")
        
        # Wait for metrics to be processed
        request_id = data.get('requestId')
        if request_id:
            print("   Waiting for metrics processing...")
            for i in range(10):  # Wait up to 10 seconds
                time.sleep(1)
                try:
                    metrics_url = f"{BASE_URL}/api/chat-metrics?request_id={request_id}"
                    metrics_response = requests.get(metrics_url)
                    metrics_data = metrics_response.json()
                    
                    if metrics_data.get('status') == 'ready':
                        metrics = metrics_data.get('metrics', {})
                        print(f"   ✅ Metrics Ready:")
                        print(f"     Accuracy: {metrics.get('accuracy_score', 'N/A')}")
                        print(f"     Grounding: {metrics.get('grounding_score', 'N/A')}")
                        print(f"     Relevance: {metrics.get('relevance_score', 'N/A')}")
                        print(f"     Flag Status: {metrics.get('guardrail_status', 'N/A')}")
                        if metrics.get('flag_auto_disabled'):
                            print(f"     🚨 FLAG AUTO-DISABLED: {metrics.get('flag_disable_reason')}")
                        break
                    elif metrics_data.get('status') == 'pending':
                        print(f"     Still processing... ({i+1}/10)")
                    else:
                        print(f"     Unknown status: {metrics_data.get('status')}")
                        break
                except:
                    print(f"     Error checking metrics ({i+1}/10)")
            
        return data
        
    except requests.RequestException as e:
        print(f"❌ Failed to send chat message: {e}")
        return None

def main():
    """Run all tests"""
    print("🧪 Testing Guardrail Clamp System")
    print("=" * 50)
    
    # Check if the server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server not healthy. Make sure your FastAPI server is running on port 8000")
            return
    except:
        print("❌ Cannot connect to server. Make sure your FastAPI server is running on port 8000")
        print("   Run: cd backend && python fastapi_wrapper.py")
        return
    
    print("\n1. Testing Initial Status")
    initial_status = test_guardrail_status()
    
    if not initial_status or not initial_status.get('api_client_enabled'):
        print("\n⚠️  LaunchDarkly API client not enabled. Check your environment variables:")
        print("   LD_API_TOKEN")
        print("   LAUNCHDARKLY_PROJECT_KEY")
        print("   LAUNCHDARKLY_ENVIRONMENT_KEY")
        print("   LAUNCHDARKLY_FLAG_KEY")
        return
    
    print("\n2. Testing Metrics Endpoint")
    test_metrics()
    
    print("\n3. Testing Chat to Generate Metrics")
    test_chat_to_generate_metrics()
    
    print("\n4. Testing Manual Flag Disable")
    test_manual_disable()
    
    print("\n5. Checking Status After Disable")
    test_guardrail_status()
    
    print("\n6. Testing Flag Recovery")
    test_recovery()
    
    print("\n7. Testing Cooldown Reset")
    test_reset_cooldowns()
    
    print("\n8. Final Status Check")
    test_guardrail_status()
    
    print("\n" + "=" * 50)
    print("🎉 Testing Complete!")
    print("\nNow try using your app and monitoring /api/guardrail/status for automatic flag disabling")
    print("when guardrail thresholds are exceeded.")

if __name__ == "__main__":
    main() 