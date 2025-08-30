#!/usr/bin/env python3
"""
Deploy Fine-tuned Phi-2 Model to SageMaker Endpoint
"""

import os
import json
import logging
import boto3
import sagemaker
from sagemaker.huggingface import HuggingFaceModel
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer
import argparse
from datetime import datetime
from sagemaker.session import SessionSettings
import tarfile
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# AWS Configuration
AWS_PROFILE = "bedrock-561"
REGION = "us-west-2"

# Model Configuration
MODEL_NAME = "phi2-compliance-analyzer"
ENDPOINT_NAME = f"{MODEL_NAME}-{datetime.now().strftime('%Y%m%d-%H%M')}"
INSTANCE_TYPE = "ml.g5.xlarge"  # Switched to avoid g5.2xlarge quota limit
TMP_CODE_DIR = "tmp/inference_code"
TMP_MODEL_DIR = "tmp/minimodel"

# S3 Configuration
S3_BUCKET = "arnav-finetune-1756054916"
MODEL_S3_PATH = "s3://sagemaker-us-west-2-561947681110/phi2-fixed-2058/output/model.tar.gz"  # From successful training job

# IAM Role - Use the same role that was used for training
SAGEMAKER_ROLE = "arn:aws:iam::561947681110:role/SageMakerExecutionRole"

def setup_aws_session():
    """Setup AWS session with profile"""
    logger.info(f"🔧 Setting up AWS session with profile: {AWS_PROFILE}")
    # Use a custom local download dir to avoid small default tmp
    local_tmp = os.path.expanduser("~/tmp_sagemaker_cache")
    os.makedirs(local_tmp, exist_ok=True)
    os.environ.setdefault("TMPDIR", local_tmp)
    settings = SessionSettings(local_download_dir=local_tmp)

    session = boto3.Session(profile_name=AWS_PROFILE, region_name=REGION)
    sagemaker_session = sagemaker.Session(boto_session=session, settings=settings)
    return session, sagemaker_session

def create_inference_script():
    """Create a minimal inference script in a temp source dir (base + LoRA)."""
    os.makedirs(TMP_CODE_DIR, exist_ok=True)
    inference_code = '''
import os, json, torch, logging, glob, tarfile, tempfile
import boto3
from urllib.parse import urlparse
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

logger = logging.getLogger(__name__)

def _disable_flash_attention():
    try:
        torch.backends.cuda.enable_flash_sdp(False)
        torch.backends.cuda.enable_mem_efficient_sdp(False)
        torch.backends.cuda.enable_math_sdp(True)
    except Exception:
        pass

def _find_adapter_dir(root_dir):
    for path in glob.glob(os.path.join(root_dir, "**", "adapter_config.json"), recursive=True):
        return os.path.dirname(path)
    return root_dir

def _sanitize_adapter_config(adapter_dir):
    config_path = os.path.join(adapter_dir, "adapter_config.json")
    if not os.path.exists(config_path):
        return adapter_dir
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
    except Exception:
        return adapter_dir
    allowed = {
        "r","lora_alpha","target_modules","lora_dropout","bias","task_type",
        "inference_mode","fan_in_fan_out","modules_to_save","init_lora_weights"
    }
    removed = [k for k in list(data.keys()) if k not in allowed]
    if removed:
        for k in removed:
            data.pop(k, None)
        with open(config_path, "w") as f:
            json.dump(data, f)
        logger.warning(f"Sanitized adapter_config.json; removed keys: {removed}")
    return adapter_dir

def _download_and_extract_s3_tar(s3_uri, extract_dir):
    os.makedirs(extract_dir, exist_ok=True)
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    tmp_tar = os.path.join(tempfile.gettempdir(), "model.tar.gz")
    s3 = boto3.client("s3")
    logger.info(f"Downloading model artifact from s3://{bucket}/{key} -> {tmp_tar}")
    s3.download_file(bucket, key, tmp_tar)
    logger.info(f"Extracting artifact to {extract_dir}")
    with tarfile.open(tmp_tar, "r:gz") as t:
        t.extractall(path=extract_dir)
    return extract_dir

def model_fn(model_dir):
    base_id = os.environ.get("BASE_MODEL_ID", "microsoft/phi-2")
    hf_token = os.environ.get("HF_TOKEN")
    s3_artifact = os.environ.get("MODEL_ARTIFACT_S3")
    cache_dir = os.environ.get("TRANSFORMERS_CACHE", "/tmp/transformers_cache")
    os.makedirs(cache_dir, exist_ok=True)
    logger.info(f"Loading base model: {base_id}")
    _disable_flash_attention()

    tok = AutoTokenizer.from_pretrained(base_id, token=hf_token)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        base_id,
        token=hf_token,
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",
        trust_remote_code=False
    )

    # If MODEL_ARTIFACT_S3 is provided, download and extract adapters at runtime
    # Always use a writable temp dir for adapters to avoid read-only /opt/ml/model
    adapter_root = "/tmp/phi2_adapters"
    if s3_artifact:
        _download_and_extract_s3_tar(s3_artifact, adapter_root)

    adapter_dir = _find_adapter_dir(adapter_root)
    adapter_dir = _sanitize_adapter_config(adapter_dir)

    model = PeftModel.from_pretrained(base, adapter_dir)
    model.eval()
    return {"m": model, "t": tok}

def input_fn(body, ctype):
    if ctype != "application/json":
        raise ValueError(f"Unsupported content type: {ctype}")
    data = json.loads(body)
    if isinstance(data, dict) and "inputs" in data:
        return str(data["inputs"])  # HF format
    instr = data.get("instruction", "")
    inp = data.get("input", "")
    return f"{instr}\n\n{inp}".strip()

def predict_fn(text, mt):
    t, m = mt["t"], mt["m"]
    x = t(text, return_tensors="pt", truncation=True, max_length=512).to(m.device)
    with torch.no_grad():
        y = m.generate(**x, max_new_tokens=256, temperature=0.2, top_p=0.9, do_sample=True, pad_token_id=t.eos_token_id, eos_token_id=t.eos_token_id)
    return {"generated_text": t.decode(y[0], skip_special_tokens=True)}

def output_fn(pred, ctype):
    return json.dumps(pred)
'''
    with open(os.path.join(TMP_CODE_DIR, "inference.py"), "w") as f:
        f.write(inference_code)
    logger.info("✅ Created minimal inference script in tmp/inference_code")


def create_requirements_file():
    """Create requirements file for deployment"""
    requirements = """transformers==4.49.0
accelerate>=0.31,<0.34
peft==0.10.0
torch>=2.6.0
numpy>=1.21.0
boto3>=1.28.0
"""
    
    os.makedirs(TMP_CODE_DIR, exist_ok=True)
    with open(os.path.join(TMP_CODE_DIR, "requirements.txt"), "w") as f:
        f.write(requirements)
    
    logger.info("✅ Created requirements file in tmp/inference_code")


def package_minimal_model_artifact():
    """Create a tiny model.tar.gz containing only code/ so the container finds inference.py."""
    os.makedirs(TMP_MODEL_DIR, exist_ok=True)
    code_dir = os.path.join(TMP_MODEL_DIR, "code")
    os.makedirs(code_dir, exist_ok=True)
    # Copy files
    for name in ["inference.py", "requirements.txt"]:
        src = os.path.join(TMP_CODE_DIR, name)
        dst = os.path.join(code_dir, name)
        with open(src, "rb") as s, open(dst, "wb") as d:
            d.write(s.read())
    # Create tar.gz
    tar_path = os.path.join(TMP_MODEL_DIR, "model.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tarf:
        tarf.add(code_dir, arcname="code")
    logger.info(f"✅ Packaged minimal model artifact at {tar_path}")
    return tar_path


def upload_to_s3(local_path, bucket, key_prefix):
    s3 = boto3.client("s3")
    key = f"{key_prefix}/model.tar.gz"
    s3.upload_file(local_path, bucket, key)
    s3_uri = f"s3://{bucket}/{key}"
    logger.info(f"✅ Uploaded model artifact to {s3_uri}")
    return s3_uri


def deploy_model(sagemaker_session):
    """Deploy the model to SageMaker endpoint"""
    logger.info(f"🚀 Deploying model to endpoint: {ENDPOINT_NAME}")

    # Create HuggingFace model with script mode (no model_data). Container will use our inference.py.
    huggingface_model = HuggingFaceModel(
        role=SAGEMAKER_ROLE,
        transformers_version="4.49.0",
        pytorch_version="2.6.0",
        py_version="py312",
        entry_point="inference.py",
        source_dir=TMP_CODE_DIR,
        sagemaker_session=sagemaker_session,
        env={
            "HF_HUB_ENABLE_HF_TRANSFER": "0",
            "TRANSFORMERS_CACHE": "/tmp/transformers_cache",
            "HUGGINGFACE_HUB_CACHE": "/tmp/huggingface",
            "HF_HOME": "/tmp/hf_home",
            "XDG_CACHE_HOME": "/tmp",
            "HF_TASK": "text-generation",
            "BASE_MODEL_ID": "microsoft/phi-2",
            "MODEL_ARTIFACT_S3": os.environ.get("MODEL_ARTIFACT_S3", MODEL_S3_PATH),
            "HF_TOKEN": os.environ.get("HF_TOKEN", "")
        }
    )
    # Explicitly set bucket to avoid default bucket DNS issues
    try:
        huggingface_model.bucket = "sagemaker-us-west-2-561947681110"
    except Exception:
        pass

    # Deploy to endpoint
    logger.info(f"📦 Deploying to instance: {INSTANCE_TYPE}")
    predictor = huggingface_model.deploy(
        initial_instance_count=1,
        instance_type=INSTANCE_TYPE,
        endpoint_name=ENDPOINT_NAME,
        serializer=JSONSerializer(),
        deserializer=JSONDeserializer()
    )

    logger.info(f"✅ Model deployed successfully!")
    logger.info(f"🔗 Endpoint: {ENDPOINT_NAME}")

    return predictor

def update_existing_endpoint(sagemaker_session, endpoint_name: str):
    """Update an existing endpoint with a new model (code-only artifact) and unique endpoint-config."""
    logger.info(f"🔁 Updating existing endpoint in-place: {endpoint_name}")

    # Package minimal artifact and upload
    tar_path = package_minimal_model_artifact()
    bucket_name = "sagemaker-us-west-2-561947681110"
    key_prefix = f"mini-code-phi2/{int(time.time())}"
    model_data_uri = upload_to_s3(tar_path, bucket_name, key_prefix)

    # Create a HuggingFaceModel with model_data URI (avoids local repack)
    hf_model = HuggingFaceModel(
        model_data=model_data_uri,
        role=SAGEMAKER_ROLE,
        transformers_version="4.49.0",
        pytorch_version="2.6.0",
        py_version="py312",
        sagemaker_session=sagemaker_session,
        env={
            "HF_HUB_ENABLE_HF_TRANSFER": "0",
            "TRANSFORMERS_CACHE": "/tmp/transformers_cache",
            "HUGGINGFACE_HUB_CACHE": "/tmp/huggingface",
            "HF_HOME": "/tmp/hf_home",
            "XDG_CACHE_HOME": "/tmp",
            "HF_TASK": "text-generation",
            "BASE_MODEL_ID": "microsoft/phi-2",
            "MODEL_ARTIFACT_S3": os.environ.get("MODEL_ARTIFACT_S3", MODEL_S3_PATH),
            "HF_TOKEN": os.environ.get("HF_TOKEN", "")
        }
    )

    # Prepare container definition for the current instance type
    container_def = hf_model.prepare_container_def(INSTANCE_TYPE)

    # Create a unique model name and register model
    model_name = f"phi2-code-model-{int(time.time())}"
    sagemaker_session.create_model(
        name=model_name,
        role=SAGEMAKER_ROLE,
        container_defs=container_def,
    )

    # Create unique endpoint-config referencing the new model
    endpoint_config_name = f"{endpoint_name}-cfg-{int(time.time())}"
    production_variant = sagemaker.production_variant(
        model_name=model_name,
        instance_type=INSTANCE_TYPE,
        initial_instance_count=1,
        variant_name="AllTraffic",
    )
    sagemaker_session.create_endpoint_config(endpoint_config_name, [production_variant])

    # Update endpoint to new config (reuses the same instance; no extra quota)
    sagemaker_session.update_endpoint(endpoint_name, endpoint_config_name)
    logger.info(f"✅ Update initiated. Monitor status in console: {endpoint_name}")

    return endpoint_name

def test_endpoint(predictor):
    """Test the deployed endpoint"""
    logger.info("🧪 Testing endpoint...")
    
    # Test input
    test_input = {
        "instruction": "Analyze the following software feature to determine its geo-compliance requirements. Provide the compliance flag, the relevant law, and the reason.",
        "input": "Feature Name: EU DSA Risk & Transparency Engine\nFeature Description: Automates systemic risk assessments and DSA transparency reporting for very large online platforms (VLOP), including recommender transparency.\nSource: Cal Civ Code § 1798.99.33.PDF\n\nLaw Context (structured JSON):\n[]"
    }
    
    try:
        response = predictor.predict(test_input)
        logger.info("✅ Endpoint test successful!")
        logger.info(f"📊 Response: {json.dumps(response, indent=2)}")
        return True
    except Exception as e:
        logger.error(f"❌ Endpoint test failed: {e}")
        return False

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy Phi-2 model to SageMaker")
    parser.add_argument("--test", action="store_true", help="Test the endpoint after deployment")
    parser.add_argument("--endpoint-name", type=str, default=None, help="Existing endpoint name to update (optional)")
    args = parser.parse_args()

    try:
        # Setup AWS
        session, sagemaker_session = setup_aws_session()

        # Create deployment files
        create_inference_script()
        create_requirements_file()

        # Use provided endpoint name to update existing endpoint
        global ENDPOINT_NAME
        if args.endpoint_name:
            ENDPOINT_NAME = args.endpoint_name
            logger.info(f"🔁 Updating existing endpoint: {ENDPOINT_NAME}")
            update_existing_endpoint(sagemaker_session, ENDPOINT_NAME)
            if args.test:
                # We cannot immediately test until update completes; skip test here.
                logger.info("⏳ Skipping immediate test; endpoint update in progress.")
            logger.info("🎉 Update request submitted!")
            logger.info(f"📋 Endpoint Name: {ENDPOINT_NAME}")
            logger.info(f"🔗 Monitor: https://{REGION}.console.aws.amazon.com/sagemaker/home?region={REGION}#/endpoints/{ENDPOINT_NAME}")
            return

        # Otherwise, create a new endpoint
        predictor = deploy_model(sagemaker_session)

        if args.test:
            test_endpoint(predictor)

        logger.info("🎉 Deployment completed successfully!")
        logger.info(f"📋 Endpoint Name: {ENDPOINT_NAME}")
        logger.info(f"🔗 Monitor: https://{REGION}.console.aws.amazon.com/sagemaker/home?region={REGION}#/endpoints/{ENDPOINT_NAME}")

    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        raise

if __name__ == "__main__":
    main()
