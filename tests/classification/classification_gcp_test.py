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
from tests.sanity_shared import (
    cleanup,
    dataset_optimization_async_test,
    dataset_optimization_sync_test,
)
from tests.classification.cifar100_classes import cifar100_classes

logger = logging.getLogger(__name__)

test_dataset = OptimizationDataset(
    name="GCP test dataset",
    labelling_type=LabellingType.SingleLabelClassification,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name="cifar100bucket",
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
    dataset_optimization_sync_test(test_dataset)


@pytest.mark.asyncio
async def test_async_dataset_optimization():
    pass
    cleanup(test_dataset)
    await dataset_optimization_async_test(test_dataset)
