import logging
import os

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
from hirundo.git import GitPlainAuthBase
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_sync_test,
    get_unique_id,
)

logger = logging.getLogger(__name__)

unique_id = get_unique_id()
test_dataset = OptimizationDataset(
    name=f"TEST-STT-MASC-dataset{unique_id}",
    labelling_type=LabellingType.SpeechToText,
    language="ar",
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name=f"STT-MASC-dataset{unique_id}",
            type=StorageTypes.GIT,
            git=StorageGit(
                repo=GitRepo(
                    name=f"STT-MASC-dataset{unique_id}",
                    repository_url="https://git@hf.co/datasets/hirundo-io/MASC",
                    plain_auth=GitPlainAuthBase(
                        username="blewis-hir",
                        password=os.environ["HUGGINGFACE_ACCESS_TOKEN"],
                    ),
                ),
                branch="main",
            ),
        ),
    ),
    dataset_metadata_path="meta-old.csv",
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
