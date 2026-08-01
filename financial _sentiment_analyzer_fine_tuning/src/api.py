from fastapi import FastAPI
from pydantic import BaseModel

import torch

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)

from config import label_config


# --------------------------------------------------
# FastAPI App
# --------------------------------------------------

app = FastAPI(
    title="Financial Sentiment Analyzer",
    version="1.0.0",
    description="DistilBERT Fine-tuned Financial Sentiment Classification API",
)


# --------------------------------------------------
# Load Model
# --------------------------------------------------

MODEL_PATH = "saved_model"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH
)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH
)

model.eval()


# --------------------------------------------------
# Request Model
# --------------------------------------------------

class PredictionRequest(BaseModel):
    text: str


# --------------------------------------------------
# Response Model
# --------------------------------------------------

class PredictionResponse(BaseModel):
    text: str
    sentiment: str
    confidence: float


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "Financial Sentiment Analyzer API is running."
    }


# --------------------------------------------------
# Prediction Endpoint
# --------------------------------------------------

@app.post(
    "/predict",
    response_model=PredictionResponse,
)
def predict(request: PredictionRequest):

    inputs = tokenizer(
        request.text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128,
    )

    with torch.no_grad():

        outputs = model(**inputs)

    logits = outputs.logits

    probabilities = torch.softmax(
        logits,
        dim=-1
    )

    predicted_class = torch.argmax(
        probabilities,
        dim=-1
    ).item()

    confidence = probabilities[0][predicted_class].item()

    sentiment = label_config.ID2LABEL[predicted_class]

    return PredictionResponse(
        text=request.text,
        sentiment=sentiment,
        confidence=round(confidence * 100, 2),
    )