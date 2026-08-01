# Financial Sentiment Analyzer using DistilBERT Fine-Tuning

## Overview

This project demonstrates an end-to-end **Natural Language Processing (NLP)** workflow by fine-tuning a pretrained **DistilBERT** model for **Financial Sentiment Classification**. The model classifies financial news headlines into one of three sentiment categories:

* Positive
* Neutral
* Negative

The project covers the complete machine learning pipeline, including data preprocessing, tokenization, model fine-tuning, evaluation, inference, and model deployment preparation using Hugging Face Transformers.

---

## Problem Statement

General-purpose language models understand English well but may not accurately interpret **financial terminology**.

For example:

> "The company reduced its workforce."

In general English, this sentence appears negative.

However, in the financial domain, workforce reduction may improve profitability and be interpreted positively by investors.

To improve domain-specific understanding, the pretrained DistilBERT model is fine-tuned using labeled financial news.

---

## Project Objectives

* Fine-tune a pretrained DistilBERT model for financial sentiment classification.
* Learn the complete supervised fine-tuning workflow.
* Evaluate model performance using industry-standard metrics.
* Build an inference-ready sentiment classification model.
* Understand the internal working of Hugging Face Trainer.

---

## Dataset

**Dataset:** Financial PhraseBank

The dataset contains manually labeled financial news sentences.

### Classes

* Positive
* Neutral
* Negative

### Dataset Version Used

```
sentences_75agree
```

This version contains sentences where at least **75% of financial experts agreed** on the sentiment label.

---

## Technology Stack

| Category      | Technology                |
| ------------- | ------------------------- |
| Language      | Python 3.11/3.12          |
| Deep Learning | PyTorch                   |
| NLP           | Hugging Face Transformers |
| Dataset       | Hugging Face Datasets     |
| Evaluation    | Scikit-learn              |
| API           | FastAPI                   |
| Deployment    | Docker                    |

---

# Project Structure

```text
financial-sentiment-analyzer/
│
├── src/
│   ├── train.py
│   ├── evaluate.py
│   ├── predict.py
│   ├── api.py
│   └── config.py
│
├── notebooks/
│   └── 01_dataset_exploration.ipynb
│
├── saved_model/
│
├── requirements.txt
├── Dockerfile
├── README.md
└── .gitignore
```

---

# Machine Learning Pipeline

```text
Financial News
       │
       ▼
Tokenizer
       │
       ▼
Input IDs + Attention Mask
       │
       ▼
DistilBERT Encoder
       │
       ▼
Classification Head
       │
       ▼
Prediction
       │
       ▼
CrossEntropy Loss
       │
       ▼
Backpropagation
       │
       ▼
Weight Update
```

---

# Data Preprocessing

The following preprocessing steps were performed before training:

* Dataset loading
* Train/Test split
* Label encoding
* Tokenization
* Attention mask generation
* Sequence padding
* Sequence truncation

Tokenizer used:

```
distilbert-base-uncased
```

Configuration:

```python
padding="max_length"
max_length=128
truncation=True
```

---

# Model Architecture

Base Model

```
DistilBERT
```

Task

```
Sequence Classification
```

Architecture

```text
Input Text

↓

Tokenizer

↓

DistilBERT Encoder

↓

PreClassifier

↓

Dropout

↓

Classification Head

↓

Positive / Neutral / Negative
```

---

# Fine-Tuning Strategy

This project uses **Standard Fine-Tuning**.

### Updated Parameters

* DistilBERT Encoder
* Classification Head

Unlike Feature Extraction or LoRA, all trainable weights are updated during training.

---

# Training Configuration

| Hyperparameter        |                   Value |
| --------------------- | ----------------------: |
| Model                 | distilbert-base-uncased |
| Epochs                |                       3 |
| Learning Rate         |                    2e-5 |
| Train Batch Size      |                      16 |
| Evaluation Batch Size |                      16 |
| Weight Decay          |                    0.01 |
| Evaluation Strategy   |             Every Epoch |
| Optimizer             |                   AdamW |

---

# Evaluation Metrics

The model is evaluated using:

* Validation Loss
* Accuracy
* Precision
* Recall
* F1 Score

Evaluation is performed after every epoch using the validation dataset.

---

# Training Results

## Epoch 1

| Metric          |      Value |
| --------------- | ---------: |
| Training Loss   | **0.3644** |
| Validation Loss | **0.1978** |
| Accuracy        | **93.82%** |
| Precision       | **93.86%** |
| Recall          | **93.82%** |
| F1 Score        | **93.82%** |

> **Note:** Replace this table with the final metrics from the last epoch after training completes.

---

# Internal Training Flow

```text
Training Dataset

↓

Batch Generation

↓

Forward Pass

↓

Prediction

↓

CrossEntropy Loss

↓

Backward Pass

↓

Gradient Computation

↓

Optimizer Step

↓

Weight Update

↓

Next Batch

↓

Next Epoch
```

---

# Evaluation Flow

```text
Validation Dataset

↓

Forward Pass

↓

Prediction

↓

Compare with Ground Truth

↓

Validation Loss

↓

Accuracy

↓

Precision

↓

Recall

↓

F1 Score
```

> During evaluation, **no gradients are computed and model weights are not updated**.

---

# Sample Prediction

Input

```text
Apple reports record quarterly profits despite market uncertainty.
```

Output

```json
{
    "label": "Positive",
    "score": 0.98
}
```

---

# Key Learnings

Through this project, I gained hands-on experience with:

* Transformer-based text classification
* Hugging Face Transformers
* Dataset preprocessing
* Tokenization
* Attention masks
* Sequence padding and truncation
* Standard Fine-Tuning
* Hugging Face Trainer
* CrossEntropy Loss
* Model evaluation
* Inference pipeline
* Model serialization

---

# Future Improvements

* LoRA (Low-Rank Adaptation)
* QLoRA Fine-Tuning
* Hyperparameter Optimization
* Early Stopping
* Learning Rate Scheduling
* Model Quantization
* ONNX Export
* FastAPI Deployment
* Dockerized REST API
* MLflow / Weights & Biases Experiment Tracking

---

# How to Run

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Train the Model

```bash
python src/train.py
```

---

## Evaluate

```bash
python src/evaluate.py
```

---

## Predict

```bash
python src/predict.py
```

---

## Start REST API

```bash
uvicorn src.api:app --reload
```

---

# Skills Demonstrated

* Natural Language Processing (NLP)
* Transformer Models
* DistilBERT
* Supervised Fine-Tuning
* Hugging Face Transformers
* PyTorch
* Data Preprocessing
* Tokenization
* Model Evaluation
* FastAPI
* Docker
* Production-Oriented AI Workflow

---

# References

* Hugging Face Transformers
* Hugging Face Datasets
* Financial PhraseBank Dataset
* PyTorch Documentation
* Scikit-learn Documentation

---

