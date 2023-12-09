from . import Generator
from .tabu.tabula import Tab
from synthtab.console import console

import pandas as pd
import torch
import typing as tp
from huggingface_hub import hf_hub_download
import joblib

REPO_ID = "omaralvarez/tabula"
FILENAME = "model.pt"


class Tabula(Generator):
    """Tabula Class

    The Tabula class handles the whole generation flow. It is used to fine-tune a large language model for tabular data,
    and to sample synthetic tabular data.

    Attributes:
        llm (str): HuggingFace checkpoint of a pretrained large language model, used a basis of our model
        tokenizer (AutoTokenizer): Tokenizer, automatically downloaded from llm-checkpoint
        model (AutoModelForCausalLM): Large language model, automatically downloaded from llm-checkpoint
        experiment_dir (str): Directory, where the training checkpoints will be saved
        epochs (int): Number of epochs to fine-tune the model
        batch_size (int): Batch size used for fine-tuning
        train_hyperparameters (dict): Additional hyperparameters added to the TrainingArguments used by the
         HuggingFaceLibrary, see here the full list of all possible values
         https://huggingface.co/docs/transformers/main/en/main_classes/trainer#transformers.TrainingArguments
        columns (list): List of all features/columns of the tabular dataset
        num_cols (list): List of all numerical features/columns of the tabular dataset
        conditional_col (str): Name of a feature/column on which the sampling can be conditioned
        conditional_col_dist (dict | list): Distribution of the feature/column specified by condtional_col
    """

    def __init__(
        self,
        dataset,
        llm: str = "distilgpt2",
        experiment_dir: str = "trainer_tabula",
        epochs: int = 100,
        batch_size: int = 8,
        max_tries_per_batch: int = 1338,
        categorical_columns: list = [],
        resume_from_checkpoint: tp.Union[bool, str] = False,
        # Generation options
        start_col: tp.Optional[str] = "",
        start_col_dist: tp.Optional[tp.Union[dict, list]] = None,
        temperature: float = 0.7,
        k: int = 100,
        max_length: int = 100,
        device: str = "cuda",
    ) -> None:
        super().__init__(dataset, batch_size, max_tries_per_batch)
        self.__name__ = "Tabula"
        self.data = self.dataset.get_single_df()
        self.categorical_columns = categorical_columns
        self.llm = llm
        self.experiment_dir = experiment_dir
        self.resume_from_checkpoint = resume_from_checkpoint
        self.epochs = epochs
        self.start_col = start_col
        self.start_col_dist = start_col_dist
        self.temperature = temperature
        self.k = k
        self.max_length = max_length
        self.device = device

        self.model = Tab(
            llm=self.llm,
            experiment_dir=self.experiment_dir,
            batch_size=self.batch_size,
            epochs=self.epochs,
            categorical_columns=self.categorical_columns,
        )

        path = hf_hub_download(repo_id=REPO_ID, filename=FILENAME)
        # Comment this block out to test tabula starting from randomly initialized model.
        # Comment this block out when uses tabula_middle_padding
        self.model.model.load_state_dict(torch.load(path), strict=False)

    def preprocess(self) -> None:
        return super().preprocess()

    def train(self) -> None:
        self.model.fit(
            data=self.data,
            conditional_col=self.dataset.config["y_label"],
            resume_from_checkpoint=self.resume_from_checkpoint,
        )
        torch.save(self.model.model.state_dict(), "model_playnet.pt")

    # TODO Difference with batch_size instead of max tries
    def sample(self) -> pd.DataFrame:
        gen = self.model.sample(
            n_samples=self.max_tries_per_batch,
            start_col=self.start_col,
            start_col_dist=self.start_col_dist,
            temperature=self.temperature,
            k=self.k,
            max_length=self.max_length,
            device=self.device,
        )
        console.print(gen)
        return gen