import numpy as np
import pandas as pd

from datasets import Dataset

from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
)

from config import (
    model_config,
    label_config,
)


# ----------------------------------------
# Load Model
# ----------------------------------------

MODEL_PATH = "saved_model"

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_PATH
)


# ----------------------------------------
# Load Test Dataset
# ----------------------------------------

df = pd.read_csv("data/financial_phrasebank.csv")

df["text"] = df["text"].str.lower()

df["label"] = df["label"].map(
    label_config.LABEL2ID
)

from sklearn.model_selection import train_test_split

_, test_df = train_test_split(
    df,
    test_size=0.2,
    random_state=42,
    stratify=df["label"]
)

test_dataset = Dataset.from_pandas(test_df)


# ----------------------------------------
# Tokenize
# ----------------------------------------

def preprocess(examples):

    return tokenizer(
        examples["text"],
        truncation=True,
        padding="max_length",
        max_length=model_config.MAX_LENGTH,
    )


test_dataset = test_dataset.map(
    preprocess,
    batched=True
)


# ----------------------------------------
# Prediction
# ----------------------------------------

trainer = Trainer(
    model=model,
)

predictions = trainer.predict(test_dataset)

logits = predictions.predictions

labels = predictions.label_ids

predicted_labels = np.argmax(
    logits,
    axis=-1
)


# ----------------------------------------
# Metrics
# ----------------------------------------

accuracy = accuracy_score(
    labels,
    predicted_labels
)

precision, recall, f1, _ = precision_recall_fscore_support(
    labels,
    predicted_labels,
    average="weighted"
)

print("\nEvaluation Results")
print("-" * 40)

print(f"Accuracy  : {accuracy:.4f}")
print(f"Precision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1 Score  : {f1:.4f}")


# ----------------------------------------
# Confusion Matrix
# ----------------------------------------

print("\nConfusion Matrix")

print(
    confusion_matrix(
        labels,
        predicted_labels
    )
)


# ----------------------------------------
# Classification Report
# ----------------------------------------

print("\nClassification Report")

print(
    classification_report(
        labels,
        predicted_labels,
        target_names=[
            "Negative",
            "Neutral",
            "Positive",
        ]
    )
)