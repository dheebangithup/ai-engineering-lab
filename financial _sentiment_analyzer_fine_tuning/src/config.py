from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    """
    Model configuration.
    """

    MODEL_NAME: str = "distilbert-base-uncased"
    NUM_LABELS: int = 3
    MAX_LENGTH: int = 128


@dataclass(frozen=True)
class TrainingConfig:
    """
    Training hyperparameters.
    """

    OUTPUT_DIR: str = "./results"

    LEARNING_RATE: float = 2e-5

    TRAIN_BATCH_SIZE: int = 16
    EVAL_BATCH_SIZE: int = 16

    NUM_EPOCHS: int = 3

    WEIGHT_DECAY: float = 0.01

    LOGGING_STEPS: int = 50

    SAVE_STRATEGY: str = "epoch"
    EVAL_STRATEGY: str = "epoch"

    LOAD_BEST_MODEL_AT_END: bool = True

    SEED: int = 42


@dataclass(frozen=True)
class DataConfig:
    """
    Dataset configuration.
    """

    TRAIN_FILE: str = "data/train.csv"
    TEST_FILE: str = "data/test.csv"

    TEXT_COLUMN: str = "text"
    LABEL_COLUMN: str = "label"


@dataclass(frozen=True)
class LabelConfig:
    """
    Label mappings.
    """

    LABEL2ID = {
        "negative": 0,
        "neutral": 1,
        "positive": 2,
    }

    ID2LABEL = {
        0: "negative",
        1: "neutral",
        2: "positive",
    }


model_config = ModelConfig()
training_config = TrainingConfig()
data_config = DataConfig()
label_config = LabelConfig()