import logging
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

logger = logging.getLogger(__name__)

test_dataset = OptimizationDataset(
    name="Test dataset",
    labelling_type=LabellingType.SingleLabelClassification,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name="cifar10bucket",
            type=StorageTypes.GCP,
            gcp=StorageGCP(
                bucket_name="cifar10bucket",
                project="Hirundo-global",
            ),
        ),
        path="/pytorch-cifar/data",
    ),
    dataset_metadata_path="cifar10.csv",
    classes=[
        "airplane",
        "automobile",
        "bird",
        "cat",
        "deer",
        "dog",
        "frog",
        "horse",
        "ship",
        "truck",
    ],
)


def test_dataset_optimization():
    cleanup(test_dataset)
    dataset_optimization_sync_test(test_dataset)


@pytest.mark.asyncio
async def test_async_dataset_optimization():
    pass
    cleanup(test_dataset)
    await dataset_optimization_async_test(test_dataset)