# PHI-2 Endpoint Troubleshooting (config.json missing)

## Attributes
- **Endpoint**: `phi-2` (InService)
- **Region**: `us-west-2`
- **Error on invoke**: 400 ModelError — `/opt/ml/model` missing `config.json`
- **Training artifact**: `s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz`

## Root Cause
- The artifact likely contains **LoRA adapter weights only** (e.g., `adapter_model.bin/.safetensors`, `adapter_config.json`) and not the full Hugging Face base model files (`config.json`, `pytorch_model.bin`, tokenizer files). The default Hugging Face inference container expects a complete model at `/opt/ml/model`, hence the `config.json` error.

## Fix A (Recommended): Custom inference that loads base + adapters
Deploy with an entry script that loads the base model from the Hub, then applies adapters from `/opt/ml/model`.

- Use container: Hugging Face Inference DLC `2.5.1-transformers4.49.0-py311-cu124` (us-west-2)
- Model data (S3): your adapter artifact (`model.tar.gz`)
- Environment:
  - `HF_TASK=text-generation`
  - `HF_TOKEN=<your_hf_token>`
  - `BASE_MODEL_ID=microsoft/phi-2`
- Minimal `inference.py` (core logic only):
```python
import os, json, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

def model_fn(model_dir):
    base_id = os.environ.get("BASE_MODEL_ID", "microsoft/phi-2")
    tok = AutoTokenizer.from_pretrained(base_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    base = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.bfloat16, attn_implementation="eager")
    model = PeftModel.from_pretrained(base, model_dir)
    model.eval()
    return {"m": model, "t": tok}

def input_fn(body, ctype):
    data = json.loads(body)
    if "inputs" in data:
        return data["inputs"]
    instr = data.get("instruction", ""); inp = data.get("input", "")
    return f"{instr}\n\n{inp}".strip()

def predict_fn(text, mt):
    t, m = mt["t"], mt["m"]
    x = t(text, return_tensors="pt", truncation=True, max_length=512).to(m.device)
    with torch.no_grad():
        y = m.generate(**x, max_new_tokens=256, temperature=0.7, do_sample=True, pad_token_id=t.eos_token_id)
    return {"generated_text": t.decode(y[0], skip_special_tokens=True)}

def output_fn(pred, ctype):
    return json.dumps(pred)
```
- Console flow:
  1) Create Model → set container to HF Inference image
  2) Model data location → your adapter artifact (`model.tar.gz`)
  3) Upload `inference.py` as source (or provide a small tar with it)
  4) Set env vars above → Create model → Create endpoint config → Create endpoint

## Fix B: Merge adapters into a full model and deploy
Export a complete model with base + LoRA merged, then point the endpoint to that artifact (no custom script needed).

- Merge script (run in a notebook/instance with HF token):
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
base_id = "microsoft/phi-2"
art = "/path/to/adapter_artifact_dir"  # contents of model.tar.gz extracted
tok = AutoTokenizer.from_pretrained(base_id)
base = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.bfloat16)
model = PeftModel.from_pretrained(base, art)
merged = model.merge_and_unload()
out = "/tmp/phi2-merged"
merged.save_pretrained(out)
tok.save_pretrained(out)
```
- Tar `out/` → upload to S3 → use HF Inference container with `HF_TASK=text-generation` and that S3 `model.tar.gz` → Create endpoint.

## Test (works for both fixes)
```bash
curl -s -H "Content-Type: application/json" \
  --data '{"inputs":"Analyze the following software feature..."}' \
  https://runtime.sagemaker.us-west-2.amazonaws.com/endpoints/<ENDPOINT>/invocations
```

## Notes
- Existing `phi-2` is InService but missing base model files at `/opt/ml/model`. Either use Fix A (custom entry script) or Fix B (merged full model) to resolve.
- We also saw local deploy attempts fail due to DNS and temp disk limits; console-based deployment avoids those local environment constraints.
