import logging
import os

import pytest
from hirundo import (
    GitPlainAuth,
    GitRepo,
    HirundoCSV,
    LabelingType,
    QADataset,
    StorageConfig,
    StorageGit,
    StorageTypes,
)
from tests.dataset_qa_shared import (
    cleanup,
    dataset_qa_sync_test,
    get_unique_id,
)

logger = logging.getLogger(__name__)

unique_id = get_unique_id()
test_storage_git = StorageGit(
    repo=GitRepo(
        name=f"STT-MASC-dataset{unique_id}",
        repository_url="https://huggingface.co/datasets/hirundo-io/MASC",
        plain_auth=GitPlainAuth(
            username="blewis-hir",
            password=os.environ["HUGGINGFACE_ACCESS_TOKEN"],
        ),
    ),
    branch="main",
)
test_dataset = QADataset(
    name=f"TEST-STT-MASC-dataset{unique_id}",
    labeling_type=LabelingType.SPEECH_TO_TEXT,
    language="ar",
    storage_config=StorageConfig(
        name=f"STT-MASC-dataset{unique_id}",
        type=StorageTypes.GIT,
        git=test_storage_git,
    ),
    data_root_url=test_storage_git.get_url(path="/wavs"),
    labeling_info=HirundoCSV(
        csv_url=test_storage_git.get_url(path="/meta.csv"),
    ),
)


@pytest.fixture(autouse=True)
def cleanup_tests():
    cleanup(test_dataset)
    yield
    cleanup(test_dataset)


def test_dataset_qa():
    full_run = dataset_qa_sync_test(test_dataset, "RUN_STT_GIT_DATA_QA")
    if full_run is not None:
        assert full_run.warnings_and_errors is not None
        assert (
            full_run.warnings_and_errors.shape[0] <= 37_527
        )  # max is 100% of the original dataset rows
        assert full_run.suspects is not None
        assert full_run.suspects.shape[0] <= 10_000
    else:
        logger.info("Full dataset QA was not run!")
