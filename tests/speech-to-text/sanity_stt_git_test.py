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
    name=f"TEST-STT-RoboShaulTiny-dataset{unique_id}",
    labelling_type=LabellingType.SPEECH_TO_TEXT,
    language="he",
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name=f"STT-RoboShaulTiny-dataset{unique_id}",
            type=StorageTypes.GIT,
            git=StorageGit(
                repo=GitRepo(
                    name=f"STT-RoboShaulTiny-dataset{unique_id}",
                    repository_url="https://huggingface.co/datasets/hirundo-io/RoboShaulTiny",
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
    cleanup(test_dataset)
    yield
    cleanup(test_dataset)


def test_dataset_optimization():
    full_run = dataset_optimization_sync_test(
        test_dataset, sanity=True, alternative_env="RUN_STT_GIT_OPTIMIZATION"
    )
    if full_run is not None:
        assert full_run.warnings_and_errors.size == 0
        assert full_run.suspects.shape[0] == 209
    else:
        logger.info("Full dataset optimization was not run!")
