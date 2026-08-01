from datasets import Dataset
from transformers import AutoTokenizer

from config import model_config, data_config


class FinancialDataset:

    def __init__(self):

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_config.MODEL_NAME
        )

    def preprocess(self, examples):

        return self.tokenizer(
            examples[data_config.TEXT_COLUMN],
            truncation=True,
            padding="max_length",
            max_length=model_config.MAX_LENGTH,
        )

    def prepare_dataset(self, train_df, test_df):

        train_dataset = Dataset.from_pandas(train_df)
        test_dataset = Dataset.from_pandas(test_df)

        train_dataset = train_dataset.map(
            self.preprocess,
            batched=True
        )

        test_dataset = test_dataset.map(
            self.preprocess,
            batched=True
        )

        return train_dataset, test_dataset, self.tokenizer