#!/usr/bin/env python3
"""
Comprehensive Model Testing Script
Tests all available models for training suitability, authentication, and performance
"""

import os
import sys
import torch
import time
import logging
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForCausalLM
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveModelTester:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN")
        self.results = {}
        
        # Model categories to test
        self.model_catalog = {
            "🔥 LLaMA Family": [
                ("meta-llama/Llama-2-7b-hf", "7B", "🔒 Gated"),
                ("meta-llama/Llama-2-7b-chat-hf", "7B", "🔒 Gated"), 
                ("meta-llama/Llama-3.1-8B-Instruct", "8B", "🔒 Gated"),
                ("NousResearch/Llama-2-7b-hf", "7B", "🟡 Community"),
                ("NousResearch/Llama-2-7b-chat-hf", "7B", "🟡 Community"),
                ("huggyllama/llama-7b", "7B", "🟡 Community"),
            ],
            
            "🚀 Qwen Family": [
                ("Qwen/Qwen1.5-0.5B", "0.5B", "🟢 Open"),
                ("Qwen/Qwen1.5-1.8B", "1.8B", "🟢 Open"), 
                ("Qwen/Qwen1.5-3B", "3B", "🟢 Open"),
                ("Qwen/Qwen1.5-7B", "7B", "🟢 Open"),
                ("Qwen/Qwen1.5-14B", "14B", "🟢 Open"),
                ("Qwen/Qwen2-7B", "7B", "🟢 Open"),
                ("Qwen/Qwen2.5-1.5B", "1.5B", "🟢 Open"),
                ("Qwen/Qwen2.5-3B", "3B", "🟢 Open"),
            ],
            
            "🧠 Phi Family": [
                ("microsoft/phi-2", "2.7B", "🟢 Open"),
                ("microsoft/phi-1_5", "1.3B", "🟢 Open"),
                ("microsoft/DialoGPT-medium", "345M", "🟢 Open"),
                ("microsoft/DialoGPT-large", "762M", "🟢 Open"),
            ],
            
            "🎯 GPT Family": [
                ("gpt2", "124M", "🟢 Open"),
                ("gpt2-medium", "345M", "🟢 Open"),
                ("gpt2-large", "762M", "🟢 Open"),
                ("gpt2-xl", "1.5B", "🟢 Open"),
            ],
            
            "🌟 Other Quality Models": [
                ("google/flan-t5-large", "770M", "🟢 Open"),
                ("google/flan-t5-xl", "3B", "🟢 Open"),
                ("mistralai/Mistral-7B-v0.1", "7B", "🟢 Open"),
                ("mistralai/Mistral-7B-Instruct-v0.1", "7B", "🟢 Open"),
                ("EleutherAI/gpt-neox-20b", "20B", "🟢 Open"),
                ("bigscience/bloomz-3b", "3B", "🟢 Open"),
                ("bigscience/bloomz-7b1", "7B", "🟢 Open"),
            ]
        }

    def test_model_access(self, model_id, size, auth_status):
        """Test if model is accessible"""
        logger.info(f"🧪 Testing: {model_id} ({size}) {auth_status}")
        
        result = {
            "model": model_id,
            "size": size,
            "auth_status": auth_status,
            "tokenizer_access": False,
            "model_access": False,
            "inference_test": False,
            "training_suitable": False,
            "memory_estimate": "Unknown",
            "error": None,
            "recommendation": "❌ Not Suitable"
        }
        
        try:
            # Test tokenizer access
            start_time = time.time()
            
            tokenizer_kwargs = {"trust_remote_code": True}
            if self.hf_token and ("🔒" in auth_status or "🟡" in auth_status):
                tokenizer_kwargs["token"] = self.hf_token
            
            tokenizer = AutoTokenizer.from_pretrained(model_id, **tokenizer_kwargs)
            result["tokenizer_access"] = True
            logger.info(f"  ✅ Tokenizer loaded ({time.time() - start_time:.2f}s)")
            
            # Test model access (config only)
            model_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16,
                "device_map": "cpu"  # Keep on CPU for testing
            }
            if self.hf_token and ("🔒" in auth_status or "🟡" in auth_status):
                model_kwargs["token"] = self.hf_token
            
            model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
            result["model_access"] = True
            
            # Estimate memory requirements
            param_count = model.num_parameters()
            memory_gb = (param_count * 4) / (1024**3)  # FP32 estimate
            result["memory_estimate"] = f"{memory_gb:.1f}GB"
            logger.info(f"  ✅ Model loaded ({param_count:,} params, ~{memory_gb:.1f}GB)")
            
            # Quick inference test
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            test_prompt = "Test prompt for compliance analysis."
            inputs = tokenizer(test_prompt, return_tensors="pt", max_length=100, truncation=True)
            
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=10, do_sample=False)
                generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
                
            result["inference_test"] = True
            logger.info(f"  ✅ Inference test passed")
            
            # Evaluate training suitability
            if param_count < 1e9:  # < 1B params
                result["training_suitable"] = True
                result["recommendation"] = "🟢 Excellent for Training"
            elif param_count < 4e9:  # < 4B params  
                result["training_suitable"] = True
                result["recommendation"] = "🟡 Good for Training"
            elif param_count < 8e9:  # < 8B params
                result["recommendation"] = "🟠 Challenging but Possible"
            else:
                result["recommendation"] = "🔴 Too Large for Current Setup"
            
            # Clean up
            del model
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
        except Exception as e:
            result["error"] = str(e)[:200]
            logger.error(f"  ❌ Failed: {str(e)[:100]}")
        
        return result

    def run_comprehensive_test(self):
        """Run comprehensive model testing"""
        logger.info("🚀 Starting Comprehensive Model Testing")
        logger.info("=" * 70)
        
        if self.hf_token:
            logger.info(f"🔑 Using HF Token: {self.hf_token[:10]}...")
        else:
            logger.info("⚠️ No HF Token - testing open models only")
        
        all_results = []
        
        for category, models in self.model_catalog.items():
            logger.info(f"\n{category}")
            logger.info("-" * 50)
            
            for model_id, size, auth_status in models:
                result = self.test_model_access(model_id, size, auth_status)
                all_results.append(result)
                time.sleep(1)  # Prevent rate limiting
        
        # Generate summary report
        self.generate_report(all_results)
        return all_results

    def generate_report(self, results):
        """Generate comprehensive summary report"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 COMPREHENSIVE MODEL TEST RESULTS")
        logger.info("=" * 70)
        
        # Categorize results
        excellent = [r for r in results if "🟢 Excellent" in r["recommendation"]]
        good = [r for r in results if "🟡 Good" in r["recommendation"]]
        challenging = [r for r in results if "🟠 Challenging" in r["recommendation"]]
        accessible = [r for r in results if r["model_access"]]
        failed = [r for r in results if not r["tokenizer_access"]]
        
        logger.info(f"\n🎯 SUCCESS SUMMARY:")
        logger.info(f"  ✅ Accessible Models: {len(accessible)}/{len(results)}")
        logger.info(f"  🟢 Excellent for Training: {len(excellent)}")
        logger.info(f"  🟡 Good for Training: {len(good)}")
        logger.info(f"  🟠 Challenging: {len(challenging)}")
        logger.info(f"  ❌ Failed: {len(failed)}")
        
        if excellent:
            logger.info(f"\n🏆 TOP RECOMMENDATIONS (Excellent):")
            for result in excellent:
                logger.info(f"  ✨ {result['model']} ({result['size']}, {result['memory_estimate']})")
        
        if good:
            logger.info(f"\n🎯 GOOD OPTIONS:")
            for result in good:
                logger.info(f"  ✅ {result['model']} ({result['size']}, {result['memory_estimate']})")
        
        if accessible and not excellent and not good:
            logger.info(f"\n⚠️ ACCESSIBLE BUT CHALLENGING:")
            for result in accessible:
                logger.info(f"  🟠 {result['model']} ({result['size']}) - {result['recommendation']}")
        
        # Authentication analysis
        auth_required = [r for r in results if "🔒" in r["auth_status"] and r["model_access"]]
        open_models = [r for r in results if "🟢" in r["auth_status"] and r["model_access"]]
        
        logger.info(f"\n🔐 AUTHENTICATION ANALYSIS:")
        logger.info(f"  🟢 Open Models Working: {len(open_models)}")
        logger.info(f"  🔒 Gated Models Working: {len(auth_required)}")
        
        # Save detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"model_test_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"\n📄 Detailed report saved: {report_file}")
        
        # Final recommendation
        if excellent:
            best = sorted(excellent, key=lambda x: float(x["memory_estimate"].replace("GB", "")))[-1]
            logger.info(f"\n🎉 FINAL RECOMMENDATION: {best['model']}")
            logger.info(f"   Size: {best['size']} | Memory: {best['memory_estimate']} | Status: {best['auth_status']}")
        elif good:
            best = sorted(good, key=lambda x: float(x["memory_estimate"].replace("GB", "")))[-1]
            logger.info(f"\n🎉 BACKUP RECOMMENDATION: {best['model']}")
            logger.info(f"   Size: {best['size']} | Memory: {best['memory_estimate']} | Status: {best['auth_status']}")
        else:
            logger.info(f"\n⚠️ No suitable models found - all failed or too large")

def main():
    tester = ComprehensiveModelTester()
    results = tester.run_comprehensive_test()
    
    # Return code based on success
    suitable_models = [r for r in results if r["training_suitable"]]
    if suitable_models:
        logger.info(f"\n✅ SUCCESS: Found {len(suitable_models)} suitable models")
        sys.exit(0)
    else:
        logger.info(f"\n❌ WARNING: No suitable models found")
        sys.exit(1)

if __name__ == "__main__":
    main()
