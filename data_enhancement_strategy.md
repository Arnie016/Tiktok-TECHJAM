# Data Enhancement Strategy for LLaMA-3.1-8B Training

## 📊 Current Dataset Analysis
- **Size**: 741 examples ✅ (Good foundation)
- **Format**: Instruction-Input-Output ✅
- **Domain**: Geo-compliance analysis ✅

## 🚨 Issues Found from Phi-2 Evaluation
1. **JSON Format Inconsistency**: Model doesn't generate proper JSON
2. **Jurisdiction Hallucination**: Wrong law citations
3. **Missing Context Understanding**: Poor reasoning

## 🔧 Enhancement Plan

### 1. **JSON Format Enforcement**
**Problem**: Current outputs are inconsistent
**Solution**: Add JSON schema examples to every training sample

#### Before:
```json
{
  "output": "{\"compliance_flag\": \"Needs Geo-Compliance\", \"law\": \"FL Online Protections\", \"reason\": \"...\"}"
}
```

#### After (Enhanced):
```json
{
  "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Always respond with valid JSON containing compliance_flag, law, and reason fields.",
  "output": "{\n  \"compliance_flag\": \"Needs Geo-Compliance\",\n  \"law\": \"FL Online Protections\",\n  \"reason\": \"Based on the law context provided, this feature requires geo-specific controls.\"\n}"
}
```

### 2. **Add Few-Shot Examples**
Prepend instruction with examples:

```
Instruction: Analyze the following software feature...

Examples:
Input: Feature with no law context
Output: {"compliance_flag": "Not Enough Information", "law": "N/A", "reason": "No relevant law found"}

Input: Feature with EU DSA context
Output: {"compliance_flag": "Needs Geo-Compliance", "law": "EU DSA", "reason": "Feature requires algorithmic transparency"}

Now analyze:
[actual input]
```

### 3. **Jurisdiction Boundary Training**
Add explicit jurisdiction constraints:

```json
{
  "instruction": "CRITICAL: Only cite laws that appear in the Law Context. If no relevant law is found, respond with 'Not Enough Information'.",
  "input": "...",
  "output": "..."
}
```

### 4. **Data Quality Improvements**

#### A. **Expand Dataset Size**
- **Target**: 2000+ examples (3x current size)
- **Method**: Generate variations of existing examples
- **Focus**: Edge cases and boundary conditions

#### B. **Add Negative Examples**
- Examples with empty law context → "Not Enough Information"
- Cross-jurisdiction confusion scenarios
- Ambiguous feature descriptions

#### C. **Improve Reasoning Quality**
- Longer, more detailed explanations
- Step-by-step legal analysis
- Clear jurisdiction identification

### 5. **Training Data Structure**
```json
{
  "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Always respond with valid JSON containing exactly these fields: compliance_flag, law, reason. If no relevant law is found in the context, use 'Not Enough Information' as the compliance_flag and 'N/A' as the law.",
  "input": "[feature description with law context]",
  "output": "{\n  \"compliance_flag\": \"[Needs Geo-Compliance|Not Enough Information|Compliant]\",\n  \"law\": \"[specific law from context or N/A]\",\n  \"reason\": \"[detailed explanation based only on provided context]\"\n}"
}
```

## 🎯 Implementation Steps

### Step 1: Data Preprocessing
```bash
# Enhance existing dataset
python3 enhance_training_data.py \
  --input train_refined_v4.jsonl \
  --output train_enhanced_v5.jsonl \
  --add-json-examples \
  --add-jurisdiction-constraints \
  --expand-negatives
```

### Step 2: Quality Validation
```bash
# Validate enhanced dataset
python3 validate_training_data.py \
  --input train_enhanced_v5.jsonl \
  --check-json-format \
  --check-jurisdiction-consistency \
  --output validation_report.json
```

### Step 3: LLaMA Training
```bash
# Train LLaMA-3.1-8B with enhanced data
python3 train_llama_model.py \
  --model-id meta-llama/Meta-Llama-3.1-8B-Instruct \
  --training-data train_enhanced_v5.jsonl \
  --lora-rank 64 \
  --lora-alpha 128 \
  --instance-type ml.g5.4xlarge
```

## 📈 Expected Improvements
- **JSON Format Compliance**: 95%+ (vs current 33%)
- **Jurisdiction Accuracy**: 90%+ (vs current 0%)
- **Overall Quality Score**: 85%+ (vs current 65%)
- **Response Consistency**: Much improved

## 💾 Storage Strategy
**✅ Keep Same Approach**: LoRA adapters in S3, base model loaded at inference
- **Pros**: Cost-effective, flexible, proven architecture
- **Cons**: None significant
- **External Drive**: Use for local development and backup

## 🎯 Success Metrics
- Zero jurisdiction hallucinations
- 100% valid JSON output
- Consistent reasoning quality
- Production-ready performance
