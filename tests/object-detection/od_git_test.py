import logging

import pytest
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
    get_unique_id,
)

logger = logging.getLogger(__name__)

unique_id = get_unique_id()
test_dataset = OptimizationDataset(
    name=f"TEST-HuggingFace-BDD-100k-validation-OD-validation-dataset{unique_id}",
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


@pytest.fixture(autouse=True)
def cleanup_tests():
    cleanup(test_dataset, unique_id)
    yield
    cleanup(test_dataset, unique_id)


def test_dataset_optimization():
    full_run = dataset_optimization_sync_test(test_dataset, "RUN_OD_GIT_OPTIMIZATION")
    if full_run is not None:
        pass
        # TODO: Add add assertion for result
    else:
        logger.info("Full dataset optimization was not run!")
