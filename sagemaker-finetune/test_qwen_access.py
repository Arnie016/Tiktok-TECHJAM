#!/usr/bin/env python3
"""
Test Qwen Model Access
======================
Verify that your HF token has access to Qwen models.
"""

import os
import sys
from transformers import AutoTokenizer, AutoModelForCausalLM

def test_qwen_access():
    """Test access to Qwen models"""
    
    # Get HF token
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not found in environment variables")
        print("💡 Set it with: export HF_TOKEN='your_token_here'")
        return False
    
    print(f"🔑 Found HF token: {hf_token[:10]}...")
    
    # Test different Qwen models
    qwen_models = [
        "Qwen/Qwen1.5-0.5B-Chat",
        "Qwen/Qwen1.5-1.8B-Chat", 
        "Qwen/Qwen1.5-3B-Chat",
        "Qwen/Qwen1.5-7B-Chat",
        "Qwen/Qwen1.5-14B-Chat",
        "Qwen/Qwen2-7B-Chat",
        "Qwen/Qwen2-72B-Instruct"
    ]
    
    accessible_models = []
    
    for model_id in qwen_models:
        print(f"\n🧪 Testing: {model_id}")
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,
                token=hf_token
            )
            print(f"✅ SUCCESS: {model_id}")
            accessible_models.append(model_id)
        except Exception as e:
            print(f"❌ FAILED: {str(e)[:100]}...")
    
    print(f"\n📊 Results: {len(accessible_models)}/{len(qwen_models)} models accessible")
    
    if accessible_models:
        print("\n🎯 Accessible Models:")
        for model in accessible_models:
            print(f"  ✅ {model}")
        
        # Recommendations
        if "Qwen/Qwen1.5-14B-Chat" in accessible_models:
            print("\n🚀 RECOMMENDATION: Use Qwen/Qwen1.5-14B-Chat")
            print("   - Best performance for complex tasks")
        elif "Qwen/Qwen1.5-7B-Chat" in accessible_models:
            print("\n🚀 RECOMMENDATION: Use Qwen/Qwen1.5-7B-Chat")
            print("   - Best balance of performance and resources")
        elif "Qwen/Qwen1.5-3B-Chat" in accessible_models:
            print("\n🚀 RECOMMENDATION: Use Qwen/Qwen1.5-3B-Chat")
            print("   - Good performance with lower resource requirements")
        elif "Qwen/Qwen1.5-0.5B-Chat" in accessible_models:
            print("\n🚀 RECOMMENDATION: Use Qwen/Qwen1.5-0.5B-Chat")
            print("   - Fastest training, good for testing")
    
    return len(accessible_models) > 0

def test_specific_model(model_id):
    """Test access to a specific model"""
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not found")
        return False
    
    print(f"🧪 Testing specific model: {model_id}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            trust_remote_code=True,
            token=hf_token
        )
        print("✅ Tokenizer access: OK")
        
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            token=hf_token,
            torch_dtype="auto",
            device_map="auto"
        )
        print("✅ Model access: OK")
        print(f"✅ SUCCESS: You have access to {model_id}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific model
        model_id = sys.argv[1]
        test_specific_model(model_id)
    else:
        # Test all models
        test_qwen_access()
