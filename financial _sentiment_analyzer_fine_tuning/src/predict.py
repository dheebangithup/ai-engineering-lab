import torch

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)

from config import label_config


# --------------------------------------------------
# Load Saved Model
# --------------------------------------------------

MODEL_PATH = "saved_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH
)

model.eval()


# --------------------------------------------------
# Prediction Function
# --------------------------------------------------

def predict(text: str):

    inputs = tokenizer(
        text,
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

    return {
        "text": text,
        "prediction": label_config.ID2LABEL[predicted_class],
        "confidence": round(confidence * 100, 2),
    }


# --------------------------------------------------
# CLI
# --------------------------------------------------

if __name__ == "__main__":

    while True:

        text = input("\nEnter Financial News (type 'exit' to quit): ")

        if text.lower() == "exit":
            break

        result = predict(text)

        print("\nPrediction")
        print("-" * 40)
        print(f"Text       : {result['text']}")
        print(f"Sentiment  : {result['prediction']}")
        print(f"Confidence : {result['confidence']}%")