import logging
import os
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
                access_key_id=os.environ["AWS_ACCESS_KEY"],
                secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
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

def skip_test():
    if "FULL_TEST" in os.environ and os.environ["FULL_TEST"] == "true":
        return 0
    return 1

@pytest.mark.skipif("skip_test() == 1")
@pytest.mark.asyncio
async def test_async_dataset_optimization():
    cleanup(test_dataset)
    await dataset_optimization_async_test(test_dataset)
