import logging
import os

from hirundo import (
    GitRepo,
    LabellingType,
    OptimizationDataset,
    StorageGit,
    StorageIntegration,
    StorageLink,
    StorageTypes,
)
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_sync_test,
)

logger = logging.getLogger(__name__)

unique_id = os.getenv("UNIQUE_ID", "").replace(".", "-").replace("/", "-")
test_dataset = OptimizationDataset(
    name=f"HuggingFace-BDD-100k-validation-OD-validation-dataset{unique_id}",
    labelling_type=LabellingType.ObjectDetection,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name=f"BDD-100k-validation-dataset{unique_id}",
            type=StorageTypes.GIT,
            git=StorageGit(
                repo=GitRepo(
                    name=f"BDD-100k-validation-dataset{unique_id}",
                    repository_url="https://git@hf.co/datasets/hirundo-io/bdd100k-validation-only",
                ),
                branch="main",
            ),
        ),
        path="/BDD100K Val from Hirundo.zip/bdd100k",
    ),
    dataset_metadata_path="bdd100k.csv",
    classes=[
        "traffic light",
        "traffic sign",
        "car",
        "pedestrian",
        "bus",
        "truck",
        "rider",
        "bicycle",
        "motorcycle",
        "train",
        "other vehicle",
        "other person",
        "trailer",
    ],
)


def test_dataset_optimization():
    cleanup(test_dataset)
    full_run = dataset_optimization_sync_test(test_dataset, "RUN_OD_GIT_OPTIMIZATION")
    if full_run:
        pass
        # TODO: Add add assertion for result
    else:
        logger.info("Full dataset optimization was not run!")
    cleanup(test_dataset)
