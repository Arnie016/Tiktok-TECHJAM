#!/usr/bin/env bash
set -euo pipefail

rm -rf sagemaker-finetune

############################################
# EDIT ME (5 values)
############################################
REGION="us-west-2"                      # AWS region
BUCKET="arnav-finetune-$(date +%s)"          # unique S3 bucket name (auto)
ROLE_NAME="SageMakerExecutionRole"           # execution role for jobs
MODEL_ID="google/flan-t5-base"               # HF model id
INSTANCE_TYPE="ml.g5.2xlarge"                # or ml.g4dn.xlarge if quota
############################################

echo "==> Using AWS identity:"
aws sts get-caller-identity
echo "==> Default CLI region: $(aws configure get region || echo '(none)')"
echo "==> Operating region: ${REGION}"

# 1) S3 bucket
echo "==> Creating S3 bucket s3://${BUCKET}"
aws s3 mb "s3://${BUCKET}" --region "${REGION}"
aws s3api put-bucket-versioning --bucket "${BUCKET}" --versioning-configuration Status=Enabled

# 2) Execution Role (trust policy + least-privilege inline policy)
echo "==> Creating IAM role: ${ROLE_NAME}"
TRUST_JSON=$(mktemp)
cat > "${TRUST_JSON}" << 'JSON'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "sagemaker.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
JSON

aws iam create-role --role-name "${ROLE_NAME}" \
  --assume-role-policy-document "file://${TRUST_JSON}" >/dev/null || echo "(role exists, continue)"

POLICY_JSON=$(mktemp)
cat > "${POLICY_JSON}" << JSON
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "S3List",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::${BUCKET}" },

    { "Sid": "S3ReadTrain",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::${BUCKET}/data/*" },

    { "Sid": "S3WriteOutput",
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::${BUCKET}/output/*" },

    { "Sid": "S3AllObjects",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::*" },

    { "Sid": "LogsBasic",
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
      "Resource": "*" }
  ]
}
JSON
aws iam put-role-policy --role-name "${ROLE_NAME}" \
  --policy-name "${ROLE_NAME}-Inline" \
  --policy-document "file://${POLICY_JSON}"

ROLE_ARN=$(aws iam get-role --role-name "${ROLE_NAME}" --query 'Role.Arn' --output text)
echo "==> Execution Role ARN: ${ROLE_ARN}"

# 3) Project skeleton + sample data
echo "==> Creating local project sagemaker-finetune/"
mkdir -p sagemaker-finetune/{data,scripts}
cd sagemaker-finetune

cat > data/train.jsonl << 'EOF'
{"instruction":"What is the capital of France?","input":"","output":"Paris"}
{"instruction":"Translate 'Hello' to Spanish","input":"","output":"Hola"}
EOF

cat > data/validation.jsonl << 'EOF'
{"instruction":"Summarize: Cats are great pets because they are friendly and low maintenance.","input":"","output":"Cats are friendly, low-maintenance pets."}
EOF

aws s3 cp data/train.jsonl "s3://${BUCKET}/data/train.jsonl"
aws s3 cp data/validation.jsonl "s3://${BUCKET}/data/validation.jsonl"

# 4) Requirements (inside training container)
cat > scripts/requirements.txt << 'REQ'
transformers==4.36.0
datasets==2.19.0
accelerate==0.30.1
peft==0.11.1
bitsandbytes==0.43.1
REQ

# 5) Training script (HF + LoRA on FLAN-T5)
cat > scripts/train.py << 'PY'
import os
from datasets import load_dataset
from transformers import (AutoTokenizer, AutoModelForSeq2SeqLM,
                          DataCollatorForSeq2Seq, Trainer, TrainingArguments)
from peft import LoraConfig, get_peft_model

model_id = os.environ.get("MODEL_ID", "google/flan-t5-base")
max_len  = int(os.environ.get("MAX_LEN", "512"))
epochs   = int(os.environ.get("EPOCHS", "3"))
lr       = float(os.environ.get("LR", "5e-5"))

train_path = os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train")
val_path   = os.environ.get("SM_CHANNEL_VALIDATION", "/opt/ml/input/data/validation")
out_dir    = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")

def find_jsonl(path):
    if os.path.isfile(path): return path
    if os.path.isdir(path):
        for f in os.listdir(path):
            if f.endswith(".jsonl"):
                return os.path.join(path, f)
    return None

train_file = find_jsonl(train_path); assert train_file, "train.jsonl missing"
val_file   = find_jsonl(val_path)

train_ds = load_dataset("json", data_files=train_file, split="train")
eval_ds  = load_dataset("json", data_files=val_file, split="train") if val_file else None

tok = AutoTokenizer.from_pretrained(model_id, use_fast=True)
model = AutoModelForSeq2SeqLM.from_pretrained(model_id)

lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, bias="none",
                  target_modules=["q","v"], task_type="SEQ_2_SEQ_LM")
model = get_peft_model(model, lora)

def build_prompt(ex):
    instr = ex.get("instruction","")
    inp   = ex.get("input","")
    return instr if not inp else instr + "\\n" + inp

def preprocess(batch):
    # The keys of the batch dictionary are the column names
    # and the values are lists of strings, so we need to process
    # each example in the batch separately.
    prompts = []
    targets = []
    for i in range(len(batch["instruction"])):
        ex = {key: batch[key][i] for key in batch}
        prompts.append(build_prompt(ex))
        targets.append(ex.get("output", ""))

    X = tok(prompts, max_length=max_len, truncation=True, padding="max_length")
    with tok.as_target_tokenizer():
        y = tok(targets, max_length=max_len, truncation=True, padding="max_length")
    X["labels"] = y["input_ids"]
    return X

train_tok = train_ds.map(preprocess, batched=True, remove_columns=train_ds.column_names)
eval_tok  = eval_ds.map(preprocess, batched=True, remove_columns=eval_ds.column_names) if eval_ds else None

collator = DataCollatorForSeq2Seq(tok, model=model)

args = TrainingArguments(
    output_dir=out_dir,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=epochs,
    learning_rate=lr,
    logging_steps=50,
    evaluation_strategy="steps" if eval_tok else "no",
    save_steps=500, save_total_limit=2,
    fp16=True
)

trainer = Trainer(model=model, args=args,
                  train_dataset=train_tok, eval_dataset=eval_tok,
                  data_collator=collator, tokenizer=tok)
trainer.train()
trainer.save_model(out_dir)
tok.save_pretrained(out_dir)
PY

# 6) Job launcher
cat > launch_job.py << PY
from sagemaker.huggingface import HuggingFace
from sagemaker import Session
import boto3

ROLE_ARN = "${ROLE_ARN}"
REGION   = "${REGION}"
BUCKET   = "${BUCKET}"
MODEL_ID = "${MODEL_ID}"
INSTANCE = "${INSTANCE_TYPE}"

boto_session = boto3.Session(region_name=REGION)
sagemaker_session = Session(boto_session=boto_session)

TRAIN_S3 = f"s3://{BUCKET}/data/train.jsonl"
VAL_S3   = f"s3://{BUCKET}/data/validation.jsonl"
OUTPUT_S3 = f"s3://{BUCKET}/output"

hyper = {"EPOCHS": 3, "LR": 5e-5, "MAX_LEN": 512, "MODEL_ID": MODEL_ID}

estimator = HuggingFace(
    entry_point="train.py",
    source_dir="scripts",
    output_path=OUTPUT_S3,
    instance_type=INSTANCE,
    instance_count=1,
    role=ROLE_ARN,
    sagemaker_session=sagemaker_session,
    transformers_version="4.36",
    pytorch_version="2.1",
    py_version="py310",
    volume_size=100,
    region=REGION,
    env=hyper,
    dependencies=["scripts/requirements.txt"]
)
estimator.fit({"train": TRAIN_S3, "validation": VAL_S3})
print("Training started. Open SageMaker console → Training jobs to watch logs.")
PY

# 7) Optional: deployment helper
cat > deploy_and_test.py << PY
from sagemaker.huggingface import HuggingFaceModel
from sagemaker import Session
import json, os

sess = Session()
model_artifacts = os.environ.get("MODEL_ARTIFACTS")  # fill after training if you want
role_arn = "${ROLE_ARN}"

if not model_artifacts:
    raise SystemExit("Set MODEL_ARTIFACTS env var to the S3 model.tar.gz path from your completed job.")

hf_model = HuggingFaceModel(
    model_data=model_artifacts,
    role=role_arn,
    transformers_version="4.36",
    pytorch_version="2.1",
    py_version="py310",
)
predictor = hf_model.deploy(instance_type="${INSTANCE_TYPE}", initial_instance_count=1)
print("Endpoint name:", predictor.endpoint_name)
print(predictor.predict({"inputs": "Translate 'I love programming' to French"}))
PY

# 8) Local SDKs (to submit the job)
python3 -m pip install --user --upgrade --break-system-packages boto3 sagemaker >/dev/null

# 9) Launch training
python3 launch_job.py

echo ""
echo "=== DONE ==="
echo "Project dir: $(pwd)"
echo "Bucket: s3://${BUCKET}"
echo "Role ARN: ${ROLE_ARN}"
echo "Next: Check SageMaker console → Training jobs for logs."
echo "Tip: Replace data/*.jsonl with your real dataset and re-run python launch_job.py"
