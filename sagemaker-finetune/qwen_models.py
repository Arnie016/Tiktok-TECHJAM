#!/usr/bin/env python3
"""
Qwen Models Guide for Geo-Compliance Fine-tuning
Including distilled versions for efficient training
"""

# Qwen model configurations
QWEN_MODELS = {
    # 🟢 SMALL QWEN MODELS (Distilled) - Fast & Efficient
    "small_models": {
        "Qwen/Qwen1.5-0.5B": {
            "params": "0.5B",
            "memory": "~3GB",
            "instance": "ml.g5.2xlarge",
            "pros": ["Very fast", "Low cost", "Good for testing"],
            "cons": ["Basic reasoning"],
            "status": "🟡 Available",
            "recommendation": "Ultra-fast prototyping"
        },
        "Qwen/Qwen1.5-1.8B": {
            "params": "1.8B",
            "memory": "~6GB",
            "instance": "ml.g5.2xlarge",
            "pros": ["Fast", "Good reasoning", "Efficient"],
            "cons": ["Still limited for complex tasks"],
            "status": "🟡 Available",
            "recommendation": "Good balance of speed/performance"
        },
        "Qwen/Qwen2.5-0.5B": {
            "params": "0.5B",
            "memory": "~3GB",
            "instance": "ml.g5.2xlarge",
            "pros": ["Latest version", "Fast", "Efficient"],
            "cons": ["Basic reasoning"],
            "status": "🟡 Available",
            "recommendation": "Latest small model"
        },
        "Qwen/Qwen2.5-1.5B": {
            "params": "1.5B",
            "memory": "~5GB",
            "instance": "ml.g5.2xlarge",
            "pros": ["Latest version", "Good reasoning", "Efficient"],
            "cons": ["Still limited"],
            "status": "🟡 Available",
            "recommendation": "Latest medium model"
        }
    },
    
    # 🟡 MEDIUM QWEN MODELS - Sweet spot
    "medium_models": {
        "Qwen/Qwen1.5-4B": {
            "params": "4B",
            "memory": "~12GB",
            "instance": "ml.g5.4xlarge",
            "pros": ["Strong reasoning", "Good for compliance", "Recent"],
            "cons": ["Higher cost"],
            "status": "🟡 Available",
            "recommendation": "Sweet spot for compliance"
        },
        "Qwen/Qwen1.5-7B": {
            "params": "7B",
            "memory": "~18GB",
            "instance": "ml.g5.12xlarge",
            "pros": ["Excellent reasoning", "Very capable"],
            "cons": ["Expensive", "Memory intensive"],
            "status": "🟡 Available",
            "recommendation": "High-end option"
        },
        "Qwen/Qwen2.5-3B": {
            "params": "3B",
            "memory": "~10GB",
            "instance": "ml.g5.4xlarge",
            "pros": ["Latest version", "Strong reasoning", "Efficient"],
            "cons": ["Higher cost"],
            "status": "🟡 Available",
            "recommendation": "Latest sweet spot"
        },
        "Qwen/Qwen2.5-7B": {
            "params": "7B",
            "memory": "~18GB",
            "instance": "ml.g5.12xlarge",
            "pros": ["Latest version", "Excellent reasoning"],
            "cons": ["Expensive", "Memory intensive"],
            "status": "🟡 Available",
            "recommendation": "Latest high-end"
        }
    },
    
    # 🔴 LARGE QWEN MODELS - High performance
    "large_models": {
        "Qwen/Qwen1.5-14B": {
            "params": "14B",
            "memory": "~32GB",
            "instance": "ml.g5.24xlarge",
            "pros": ["Exceptional reasoning", "Best for complex compliance"],
            "cons": ["Very expensive", "Very memory intensive"],
            "status": "❌ Likely to fail",
            "recommendation": "Only with large budget"
        },
        "Qwen/Qwen1.5-32B": {
            "params": "32B",
            "memory": "~64GB",
            "instance": "ml.g5.48xlarge",
            "pros": ["Exceptional reasoning", "Very capable"],
            "cons": ["Extremely expensive", "Extremely memory intensive"],
            "status": "❌ Will fail",
            "recommendation": "Not recommended"
        },
        "Qwen/Qwen2.5-14B": {
            "params": "14B",
            "memory": "~32GB",
            "instance": "ml.g5.24xlarge",
            "pros": ["Latest version", "Exceptional reasoning"],
            "cons": ["Very expensive", "Very memory intensive"],
            "status": "❌ Likely to fail",
            "recommendation": "Only with large budget"
        }
    },
    
    # 🟣 DISTILLED QWEN MODELS - Specialized for efficiency
    "distilled_models": {
        "Qwen/Qwen1.5-0.5B-Chat": {
            "params": "0.5B",
            "memory": "~3GB",
            "instance": "ml.g5.2xlarge",
            "pros": ["Chat-optimized", "Fast", "Efficient"],
            "cons": ["Basic reasoning"],
            "status": "🟡 Available",
            "recommendation": "Good for dialogue tasks"
        },
        "Qwen/Qwen1.5-1.8B-Chat": {
            "params": "1.8B",
            "memory": "~6GB",
            "instance": "ml.g5.2xlarge",
            "pros": ["Chat-optimized", "Good reasoning", "Efficient"],
            "cons": ["Still limited"],
            "status": "🟡 Available",
            "recommendation": "Good for compliance Q&A"
        },
        "Qwen/Qwen2.5-0.5B-Chat": {
            "params": "0.5B",
            "memory": "~3GB",
            "instance": "ml.g5.2xlarge",
            "pros": ["Latest chat model", "Fast", "Efficient"],
            "cons": ["Basic reasoning"],
            "status": "🟡 Available",
            "recommendation": "Latest chat model"
        },
        "Qwen/Qwen2.5-1.5B-Chat": {
            "params": "1.5B",
            "memory": "~5GB",
            "instance": "ml.g5.2xlarge",
            "pros": ["Latest chat model", "Good reasoning", "Efficient"],
            "cons": ["Still limited"],
            "status": "🟡 Available",
            "recommendation": "Latest medium chat model"
        }
    }
}

# Recommended Qwen progression
QWEN_RECOMMENDED_PROGRESSION = [
    "Qwen/Qwen1.5-0.5B",           # Fastest - good for testing
    "Qwen/Qwen1.5-1.8B",           # Good balance
    "Qwen/Qwen2.5-1.5B",           # Latest medium
    "Qwen/Qwen1.5-4B",             # Sweet spot
    "Qwen/Qwen2.5-3B",             # Latest sweet spot
    "Qwen/Qwen1.5-7B"              # High-end
]

# Quick reference for Qwen models
QWEN_QUICK_REFERENCE = {
    "fastest_prototyping": "Qwen/Qwen1.5-0.5B",
    "best_budget": "Qwen/Qwen1.5-1.8B",
    "best_performance_cost": "Qwen/Qwen1.5-4B",
    "latest_medium": "Qwen/Qwen2.5-1.5B",
    "latest_sweet_spot": "Qwen/Qwen2.5-3B",
    "best_chat": "Qwen/Qwen1.5-1.8B-Chat"
}

def print_qwen_recommendations():
    """Print formatted Qwen model recommendations"""
    print("🤖 QWEN MODELS FOR GEO-COMPLIANCE FINE-TUNING")
    print("=" * 60)
    
    print("\n🟢 SMALL QWEN MODELS (Fast & Efficient):")
    for model_id, details in QWEN_MODELS["small_models"].items():
        print(f"  {model_id}")
        print(f"    Params: {details['params']} | Memory: {details['memory']} | Instance: {details['instance']}")
        print(f"    Status: {details['status']}")
        print(f"    Recommendation: {details['recommendation']}")
        print()
    
    print("\n🟡 MEDIUM QWEN MODELS (Sweet Spot):")
    for model_id, details in QWEN_MODELS["medium_models"].items():
        print(f"  {model_id}")
        print(f"    Params: {details['params']} | Memory: {details['memory']} | Instance: {details['instance']}")
        print(f"    Status: {details['status']}")
        print(f"    Recommendation: {details['recommendation']}")
        print()
    
    print("\n🔴 LARGE QWEN MODELS (High Performance):")
    for model_id, details in QWEN_MODELS["large_models"].items():
        print(f"  {model_id}")
        print(f"    Params: {details['params']} | Memory: {details['memory']} | Instance: {details['instance']}")
        print(f"    Status: {details['status']}")
        print(f"    Recommendation: {details['recommendation']}")
        print()
    
    print("\n🟣 DISTILLED QWEN MODELS (Chat-Optimized):")
    for model_id, details in QWEN_MODELS["distilled_models"].items():
        print(f"  {model_id}")
        print(f"    Params: {details['params']} | Memory: {details['memory']} | Instance: {details['instance']}")
        print(f"    Status: {details['status']}")
        print(f"    Recommendation: {details['recommendation']}")
        print()
    
    print("\n📈 RECOMMENDED QWEN PROGRESSION:")
    for i, model in enumerate(QWEN_RECOMMENDED_PROGRESSION, 1):
        print(f"  {i}. {model}")
    
    print("\n⚡ QWEN QUICK REFERENCE:")
    for scenario, model in QWEN_QUICK_REFERENCE.items():
        print(f"  {scenario}: {model}")

def get_qwen_model_details(model_id):
    """Get details for a specific Qwen model"""
    for category, models in QWEN_MODELS.items():
        if model_id in models:
            return models[model_id]
    return None

def suggest_qwen_model(current_model="microsoft/DialoGPT-medium"):
    """Suggest Qwen models based on current model"""
    if "0.5B" in current_model or "small" in current_model.lower():
        return "Qwen/Qwen1.5-0.5B", get_qwen_model_details("Qwen/Qwen1.5-0.5B")
    elif "medium" in current_model.lower() or "345M" in current_model:
        return "Qwen/Qwen1.5-1.8B", get_qwen_model_details("Qwen/Qwen1.5-1.8B")
    elif "large" in current_model.lower() or "774M" in current_model:
        return "Qwen/Qwen1.5-4B", get_qwen_model_details("Qwen/Qwen1.5-4B")
    else:
        return "Qwen/Qwen1.5-4B", get_qwen_model_details("Qwen/Qwen1.5-4B")

if __name__ == "__main__":
    print_qwen_recommendations()
    
    print("\n" + "=" * 60)
    print("💡 QWEN ADVANTAGES:")
    print("✅ Excellent reasoning capabilities")
    print("✅ Good multilingual support")
    print("✅ Recent models (Qwen2.5 is latest)")
    print("✅ Efficient training")
    print("✅ Good for compliance tasks")
    
    print("\n🎯 RECOMMENDED STARTING POINTS:")
    print("1. Qwen/Qwen1.5-0.5B (fastest)")
    print("2. Qwen/Qwen1.5-1.8B (good balance)")
    print("3. Qwen/Qwen1.5-4B (sweet spot)")
    print("4. Qwen/Qwen2.5-1.5B (latest medium)")
