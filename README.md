# Bedrock Legal AI Project

A comprehensive legal AI system built on AWS Bedrock for processing and analyzing legal documents, with focus on compliance and regulatory analysis.

## Overview

This project implements a legal AI system that:
- Processes legal documents and regulations
- Analyzes compliance requirements across multiple jurisdictions
- Trains and deploys custom models for legal text analysis
- Provides inference capabilities for legal document processing

## Features

- **Document Processing**: Convert PDFs to structured JSON format
- **Model Training**: Custom fine-tuning of language models for legal tasks
- **Compliance Analysis**: Multi-jurisdiction legal compliance checking
- **AWS Integration**: Full integration with AWS Bedrock, SageMaker, and S3
- **Evaluation Tools**: Comprehensive model evaluation and testing

## Project Structure

```
bedrock/
├── docs/                    # Documentation files
├── pdfs/                    # Source PDF documents
├── build/                   # Build artifacts
├── tmp/                     # Temporary files
├── *.py                     # Main Python scripts
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Key Components

### Core Scripts
- `retrain_phi2_v5.py` - Model training and deployment
- `inference.py` - Model inference and prediction
- `comprehensive_evaluation.py` - Model evaluation
- `batch_pdf_to_jsonl.py` - PDF processing pipeline
- `convert_techjam_append.py` - Data conversion utilities

### AWS Integration
- SageMaker model training and deployment
- S3 storage for data and models
- Bedrock integration for AI services

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **AWS Configuration**
   - Configure AWS credentials
   - Set up SageMaker permissions
   - Configure S3 buckets

3. **Environment Setup**
   - Set required environment variables
   - Configure model parameters

## Usage

### Training a Model
```bash
python retrain_phi2_v5.py
```

### Running Inference
```bash
python inference.py
```

### Evaluating Models
```bash
python comprehensive_evaluation.py
```

## Data Processing

The system supports:
- PDF to JSON conversion
- Legal document enrichment
- Multi-jurisdiction data filtering
- Training data generation

## Model Architecture

- Base model: Phi-2
- Fine-tuning approach: LoRA
- Training data: Legal documents and regulations
- Target domains: Compliance, regulatory analysis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license information here]

## Contact

[Add your contact information here]
