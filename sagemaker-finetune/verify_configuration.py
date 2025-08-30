#!/usr/bin/env python3
"""
Configuration Verification Script
================================
Verify all settings are correct before launching training.
"""

import os
import sys

def verify_configuration():
    """Verify all configuration settings"""
    print("🔍 Verifying Configuration...")
    print("=" * 50)
    
    # Check HF Token
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN not set")
        return False
    print(f"✅ HF_TOKEN: {hf_token[:10]}...")
    
    # Check model ID in launch script
    with open("launch_qwen_training.py", "r") as f:
        launch_content = f.read()
        if "Qwen/Qwen1.5-7B-Chat" in launch_content:
            print("✅ Launch script: Using Qwen/Qwen1.5-7B-Chat")
        else:
            print("❌ Launch script: Still using old model")
            return False
    
    # Check model ID in training script
    with open("scripts/train_qwen.py", "r") as f:
        train_content = f.read()
        if "Qwen/Qwen1.5-7B-Chat" in train_content:
            print("✅ Training script: Using Qwen/Qwen1.5-7B-Chat")
        else:
            print("❌ Training script: Still using old model")
            return False
    
    # Check instance type
    if "ml.g5.4xlarge" in launch_content:
        print("✅ Instance type: ml.g5.4xlarge (48GB VRAM)")
    else:
        print("❌ Instance type: Not set to ml.g5.4xlarge")
        return False
    
    # Check hyperparameters
    if "learning_rate\": 5e-5" in launch_content:
        print("✅ Learning rate: 5e-5 (optimized for 7B)")
    else:
        print("❌ Learning rate: Not optimized for 7B")
        return False
    
    if "max_seq_length\": 1024" in launch_content:
        print("✅ Max sequence length: 1024")
    else:
        print("❌ Max sequence length: Not set to 1024")
        return False
    
    print("\n🎯 Configuration Summary:")
    print("- Model: Qwen/Qwen1.5-7B-Chat")
    print("- Instance: ml.g5.4xlarge")
    print("- Learning Rate: 5e-5")
    print("- Max Length: 1024")
    print("- Token: ✅ Verified")
    
    return True

if __name__ == "__main__":
    if verify_configuration():
        print("\n✅ ALL CHECKS PASSED - Ready for training!")
        print("\n🚀 Launch command:")
        print("python3 launch_qwen_training.py --model-id 'Qwen/Qwen1.5-7B-Chat'")
    else:
        print("\n❌ Configuration issues found - Please fix before training")
        sys.exit(1)






