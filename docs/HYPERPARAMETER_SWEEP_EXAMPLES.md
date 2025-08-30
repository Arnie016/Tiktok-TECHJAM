# Hyperparameter Sweep - Specific Test Examples

## 🔬 **Comprehensive Testing Results**

**Date**: August 28, 2025  
**Model**: `geo-compliance-endpoint-fixed-lora`  
**Total Tests**: 168 combinations  
**Success Rate**: 0% (No valid JSON generated)

---

## 📋 **Test Structure**

### **Features Tested:**
1. **UT Parental Consent & Curfew** - Utah minor protection features
2. **US CSAM Reporting Pipeline** - Child safety reporting system  
3. **User Data Export Tool** - GDPR data portability feature

### **Parameter Combinations Tested:**
- **Temperature**: 0.05, 0.1, 0.2, 0.4, 0.8
- **Top-p**: 0.5, 0.6, 0.7, 0.8, 0.9
- **Max Tokens**: 50, 200, 500
- **Sampling**: Deterministic vs Stochastic

### **Prompt Styles Tested:**
- **Detailed**: Full examples + schema
- **Simple**: Basic instruction
- **Training Format**: Matches training data format
- **Minimal**: Shortest possible prompt

---

## 🎯 **Specific Test Examples**

### **Example 1: UT Parental Consent & Curfew**

**Input Prompt (Detailed Style):**
```
You are a compliance analyst. Analyze the software feature and output structured JSON only.

Output Format:
{
  "compliance_flag": "...",
  "law": "...",
  "reason": "..."
}

Example:
Input: Feature Name: Age Verification; Description: Blocks under-18 logins.
Output: {
  "compliance_flag": "Needs Geo-Compliance",
  "law": "Florida Online Protections for Minors Act",
  "reason": "The law requires under-18 protections"
}

Input: Feature Name: Data Export Tool; Description: Allows users to download their data.
Output: {
  "compliance_flag": "Needs Geo-Compliance",
  "law": "GDPR Article 20",
  "reason": "Right to data portability requires export functionality"
}

Now analyze this feature:

Feature Name: UT Parental Consent & Curfew
Feature Description: Requires verified parental consent for minor accounts in Utah and enforces nightly curfew and default privacy settings.

Output:
```

**Model Responses by Parameter:**

| Parameters | Response | Length | Status |
|------------|----------|--------|--------|
| **Very Low Temp** (0.05) | `""` | 0 chars | ❌ Empty |
| **Low Temp** (0.1) | `""` | 0 chars | ❌ Empty |
| **Medium Temp** (0.2) | `""` | 0 chars | ❌ Empty |
| **High Temp** (0.4) | `""` | 0 chars | ❌ Empty |
| **Very High Temp** (0.8) | `""` | 0 chars | ❌ Empty |

**Simple Style Prompt:**
```
Analyze this feature for geo-compliance: UT Parental Consent & Curfew - Requires verified parental consent for minor accounts in Utah and enforces nightly curfew and default privacy settings.

Output JSON with compliance_flag, law, reason:
```

**Model Responses:**

| Parameters | Response | Length | Status |
|------------|----------|--------|--------|
| **Very Low Temp** | `"''"` | 2 chars | ❌ Invalid |
| **Low Temp** | `" false"` | 5 chars | ❌ Invalid |
| **Medium Temp** | `"''"` | 2 chars | ❌ Invalid |
| **High Temp** | `"''"` | 2 chars | ❌ Invalid |
| **Very High Temp** | `"''"` | 2 chars | ❌ Invalid |

**Training Format Prompt:**
```
Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.

Feature Name: UT Parental Consent & Curfew
Feature Description: Requires verified parental consent for minor accounts in Utah and enforces nightly curfew and default privacy settings.

### Response:
```

**Model Responses:**

| Parameters | Response | Length | Status |
|------------|----------|--------|--------|
| **Very Low Temp** | `" No"` | 2 chars | ❌ Invalid |
| **Low Temp** | `" No"` | 2 chars | ❌ Invalid |
| **Medium Temp** | `" No"` | 2 chars | ❌ Invalid |
| **High Temp** | `" No"` | 2 chars | ❌ Invalid |
| **Very High Temp** | `" Not required."` | 13 chars | ❌ Invalid |

**Minimal Style Prompt:**
```
Feature: UT Parental Consent & Curfew. Description: Requires verified parental consent for minor accounts in Utah and enforces nightly curfew and default privacy settings. Generate compliance analysis as JSON.
```

**Model Responses:**

| Parameters | Response | Length | Status |
|------------|----------|--------|--------|
| **Very Low Temp** | `"parse"` | 5 chars | ❌ Invalid |
| **Low Temp** | `"parse."` | 6 chars | ❌ Invalid |
| **Medium Temp** | `"parse"` | 5 chars | ❌ Invalid |
| **High Temp** | `"parse"` | 5 chars | ❌ Invalid |
| **Very High Temp** | `"parse"` | 5 chars | ❌ Invalid |

---

### **Example 2: US CSAM Reporting Pipeline**

**Training Format Prompt:**
```
Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.

Feature Name: US CSAM Reporting Pipeline
Feature Description: Detects and reports apparent child sexual abuse material to NCMEC and preserves commingled content per federal law.

### Response:
```

**Model Responses:**

| Parameters | Response | Length | Status |
|------------|----------|--------|--------|
| **Very Low Temp** | `" 18 U.S.C. § 2258A"` | 11 chars | ❌ Invalid |
| **Low Temp** | `" 18 U.S.C. § 2258A"` | 11 chars | ❌ Invalid |
| **Medium Temp** | `" 18 U.S.C. § 2258A"` | 11 chars | ❌ Invalid |
| **High Temp** | `" 18 U.S.C. § 2258A"` | 11 chars | ❌ Invalid |
| **Very High Temp** | `" 18 U.S.C. § 2258A"` | 11 chars | ❌ Invalid |

---

### **Example 3: User Data Export Tool**

**Training Format Prompt:**
```
Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.

Feature Name: User Data Export Tool
Feature Description: Allows users to download their personal data in machine-readable format.

### Response:
```

**Model Responses:**

| Parameters | Response | Length | Status |
|------------|----------|--------|--------|
| **Very Low Temp** | `" GDPR Article 20"` | 21 chars | ❌ Invalid |
| **Low Temp** | `" GDPR Article 20"` | 21 chars | ❌ Invalid |
| **Medium Temp** | `" GDPR Article 20"` | 21 chars | ❌ Invalid |
| **High Temp** | `" GDPR Article 20"` | 21 chars | ❌ Invalid |
| **Very High Temp** | `" GDPR Article 20"` | 21 chars | ❌ Invalid |

---

## 📊 **Response Pattern Analysis**

### **Response Categories:**

1. **Empty Responses** (0 chars): 42 tests (25%)
   - All "detailed" style prompts
   - Model completely silent

2. **Very Short Responses** (2-6 chars): 126 tests (75%)
   - `"''"` (2 chars) - Empty quotes
   - `" No"` (2 chars) - Simple negation
   - `"parse"` (5 chars) - Random word
   - `" false"` (5 chars) - Boolean response

3. **Slightly Longer Responses** (11-21 chars): 27 tests (16%)
   - `" 18 U.S.C. § 2258A"` (11 chars) - Law citation only
   - `" GDPR Article 20"` (21 chars) - Law citation only
   - `" Not required."` (13 chars) - Simple statement

### **Key Observations:**

1. **No JSON Structure**: Zero responses contained valid JSON
2. **No Task Understanding**: Model doesn't understand the compliance analysis task
3. **Random Words**: Responses like "parse", "false", "txt", "com"
4. **Law Citations Only**: Some responses mention laws but no structured output
5. **Prompt Insensitive**: All prompt styles produce similar poor results

---

## 🎯 **Expected vs Actual Output**

### **Expected Output (from training data):**
```json
{
  "compliance_flag": "Needs Geo-Compliance",
  "law": "Utah Social Media Regulation Act art 1",
  "reason": "Utah mandates verified parental consent, curfew, and minors' privacy protections. Referenced art 1."
}
```

### **Actual Outputs:**
- `""` (empty)
- `"''"` (empty quotes)
- `" No"` (simple negation)
- `"parse"` (random word)
- `" 18 U.S.C. § 2258A"` (law citation only)

---

## 💡 **Conclusions**

### **Model Behavior:**
1. **Completely Failed**: 0% success rate across all 168 tests
2. **No Task Learning**: Model didn't learn the compliance analysis task
3. **Random Output**: Responses appear to be random tokens
4. **No JSON Generation**: Zero structured output capability

### **Root Cause:**
1. **Model Too Small**: 345M parameters insufficient for complex task
2. **Training Data Insufficient**: 129 examples too small
3. **Base Model Mismatch**: DialoGPT designed for conversation, not structured output
4. **Task Complexity**: JSON generation + legal reasoning requires larger model

### **Recommendations:**
1. **Upgrade Model**: Use 7B+ parameter instruction model
2. **More Training Data**: Increase to 500-1000 examples
3. **Instruction Format**: Use instruction-tuned base model
4. **Retrain**: Complete retraining with larger model

---

**Status**: ❌ **CRITICAL FAILURE** - Model incapable of required task


