import logging

import pytest
from hirundo import (
    GitRepo,
    HirundoCSV,
    LabelingType,
    OptimizationDataset,
    StorageConfig,
    StorageGit,
    StorageTypes,
)
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_sync_test,
    get_unique_id,
)

logger = logging.getLogger(__name__)

unique_id = get_unique_id()
git_storage = StorageGit(
    repo=GitRepo(
        name=f"BDD-100k-validation-dataset{unique_id}",
        repository_url="https://huggingface.co/datasets/hirundo-io/bdd100k-validation-only",
    ),
    branch="main",
)
test_dataset = OptimizationDataset(
    name=f"TEST-HuggingFace-BDD-100k-validation-OD-validation-dataset{unique_id}",
    labeling_type=LabelingType.OBJECT_DETECTION,
    storage_config=StorageConfig(
        name=f"BDD-100k-validation-dataset{unique_id}",
        type=StorageTypes.GIT,
        git=git_storage,
    ),
    labeling_info=HirundoCSV(
        csv_url=git_storage.get_url(
            path="/BDD100K Val from Hirundo.zip/bdd100k/bdd100k.csv"
        ),
    ),
    data_root_url=git_storage.get_url(path="/BDD100K Val from Hirundo.zip/bdd100k"),
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
    cleanup(test_dataset)
    yield
    cleanup(test_dataset)


def test_dataset_optimization():
    full_run = dataset_optimization_sync_test(test_dataset, "RUN_OD_GIT_OPTIMIZATION")
    if full_run is not None:
        pass
        # TODO: Add add assertion for result
    else:
        logger.info("Full dataset optimization was not run!")
