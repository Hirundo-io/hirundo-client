import json
import logging
import os
import pytest
from hirundo import (
    OptimizationDataset,
    LabellingType,
    StorageLink,
    StorageIntegration,
    StorageTypes,
    StorageGCP,
)
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_async_test,
    dataset_optimization_sync_test,
    skip_test,
)
from tests.classification.cifar100_classes import cifar100_classes

logger = logging.getLogger(__name__)

unique_id = os.getenv("UNIQUE_ID", "").replace(".", "-")
test_dataset = OptimizationDataset(
    name=f"GCP cifar 100 classification dataset{unique_id}",
    labelling_type=LabellingType.SingleLabelClassification,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name=f"cifar100bucket{unique_id}",
            type=StorageTypes.GCP,
            gcp=StorageGCP(
                bucket_name="cifar100bucket",
                project="Hirundo-global",
                credentials_json=json.loads(os.environ["GCP_CREDENTIALS"]),
            ),
        ),
        path="/pytorch-cifar/data",
    ),
    dataset_metadata_path="cifar100.csv",
    classes=cifar100_classes,
)


def test_dataset_optimization():
    cleanup(test_dataset)
    full_run = dataset_optimization_sync_test(test_dataset, "RUN_CLASSIFICATION_GCP_OPTIMIZATION")
    if full_run:
        pass
        # TODO: Add add assertion for result
    else:
        logger.info("Full dataset optimization was not run!")
