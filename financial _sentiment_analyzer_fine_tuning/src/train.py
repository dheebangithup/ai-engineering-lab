import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support
)

from transformers import (
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)

from dataset import FinancialDataset

from config import (
    model_config,
    training_config,
    label_config,
)


# --------------------------------------------------
# Load Dataset
# --------------------------------------------------

df = pd.read_csv("data/financial_phrasebank.csv")


# --------------------------------------------------
# Basic Cleaning
# --------------------------------------------------

df["text"] = df["text"].map(
    lambda x: x.lower() if isinstance(x, str) else x
)


# --------------------------------------------------
# Label Encoding
# --------------------------------------------------

df["label"] = df["label"].map(
    label_config.LABEL2ID
)


# --------------------------------------------------
# Train Test Split
# --------------------------------------------------

train_df, test_df = train_test_split(
    df,
    test_size=0.2,
    random_state=training_config.SEED,
    stratify=df["label"]
)


# --------------------------------------------------
# Prepare Dataset
# --------------------------------------------------

dataset_builder = FinancialDataset()

train_dataset, test_dataset, tokenizer = dataset_builder.prepare_dataset(
    train_df,
    test_df,
)


# --------------------------------------------------
# Load Model
# --------------------------------------------------

model = AutoModelForSequenceClassification.from_pretrained(
    model_config.MODEL_NAME,
    num_labels=model_config.NUM_LABELS,
)

model.config.label2id = label_config.LABEL2ID
model.config.id2label = label_config.ID2LABEL


# --------------------------------------------------
# Metrics
# --------------------------------------------------

def compute_metrics(eval_pred):

    logits, labels = eval_pred

    predictions = np.argmax(
        logits,
        axis=-1
    )

    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average="weighted"
    )

    accuracy = accuracy_score(
        labels,
        predictions
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


# --------------------------------------------------
# Training Arguments
# --------------------------------------------------

training_args = TrainingArguments(

    output_dir=training_config.OUTPUT_DIR,

    learning_rate=training_config.LEARNING_RATE,

    per_device_train_batch_size=training_config.TRAIN_BATCH_SIZE,

    per_device_eval_batch_size=training_config.EVAL_BATCH_SIZE,

    num_train_epochs=training_config.NUM_EPOCHS,

    weight_decay=training_config.WEIGHT_DECAY,

    logging_steps=training_config.LOGGING_STEPS,

    eval_strategy=training_config.EVAL_STRATEGY,

    save_strategy=training_config.SAVE_STRATEGY,

    load_best_model_at_end=training_config.LOAD_BEST_MODEL_AT_END,

    report_to="none",
)


# --------------------------------------------------
# Trainer
# --------------------------------------------------

trainer = Trainer(

    model=model,

    args=training_args,

    train_dataset=train_dataset,

    eval_dataset=test_dataset,

    processing_class=tokenizer,

    compute_metrics=compute_metrics,

)


# --------------------------------------------------
# Train
# --------------------------------------------------

trainer.train()


# --------------------------------------------------
# Evaluate
# --------------------------------------------------

metrics = trainer.evaluate()

print(metrics)


# --------------------------------------------------
# Save Model
# --------------------------------------------------

trainer.save_model("saved_model")

tokenizer.save_pretrained("saved_model")


print("\nTraining Completed Successfully.")