import logging
import pytest
from hirundo import (
    OptimizationDataset,
    LabellingType,
    StorageLink,
    StorageIntegration,
    StorageTypes,
    StorageS3,
)
from tests.sanity_shared import cleanup, dataset_optimization_async_test, dataset_optimization_sync_test

logger = logging.getLogger(__name__)

test_dataset = OptimizationDataset(
    name="AWS test dataset",
    labelling_type=LabellingType.SingleLabelClassification,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name="cifar10bucket",
            type=StorageTypes.S3,
            s3=StorageS3(
                bucket_url="s3://cifar10bucket",
                region_name="us-east-2",
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

@pytest.mark.skip(reason="Still need to implement AWS S3 Bucket auth")
def test_dataset_optimization():
    cleanup(test_dataset)
    dataset_optimization_sync_test(test_dataset)


@pytest.mark.skip(reason="Still need to implement AWS S3 Bucket auth")
@pytest.mark.asyncio
async def test_async_dataset_optimization():
    cleanup(test_dataset)
    await dataset_optimization_async_test(test_dataset)
