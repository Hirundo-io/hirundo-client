import json
import logging
import os

import pytest
from hirundo import (
    HirundoCSV,
    LabelingType,
    OptimizationDataset,
    StorageGCP,
    StorageIntegration,
    StorageTypes,
)
from tests.classification.cifar100_classes import cifar100_classes
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_sync_test,
    get_unique_id,
)

logger = logging.getLogger(__name__)

unique_id = get_unique_id()
gcp_bucket = StorageGCP(
    bucket_name="cifar100bucket",
    project="Hirundo-global",
    credentials_json=json.loads(os.environ["GCP_CREDENTIALS"]),
)
test_dataset = OptimizationDataset(
    name=f"TEST-GCP cifar 100 classification dataset{unique_id}",
    labeling_type=LabelingType.SINGLE_LABEL_CLASSIFICATION,
    storage_integration=StorageIntegration(
        name=f"cifar100bucket{unique_id}",
        type=StorageTypes.GCP,
        gcp=gcp_bucket,
    ),
    data_root_url=gcp_bucket.get_url(path="/pytorch-cifar/data"),
    labeling_info=HirundoCSV(
        csv_url=gcp_bucket.get_url(path="/pytorch-cifar/data/cifar100.csv"),
    ),
    classes=cifar100_classes,
)


@pytest.fixture(autouse=True)
def cleanup_tests():
    cleanup(test_dataset)
    yield
    cleanup(test_dataset)


def test_dataset_optimization():
    full_run = dataset_optimization_sync_test(
        test_dataset, "RUN_CLASSIFICATION_GCP_OPTIMIZATION"
    )
    if full_run is not None:
        assert full_run.warnings_and_errors.size == 0
        # TODO: Add more assertions for results
    else:
        logger.info("Full dataset optimization was not run!")
