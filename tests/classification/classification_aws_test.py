import logging
import os

from hirundo import (
    LabellingType,
    OptimizationDataset,
    StorageIntegration,
    StorageLink,
    StorageS3,
    StorageTypes,
)
from tests.dataset_optimization_shared import cleanup, dataset_optimization_sync_test

logger = logging.getLogger(__name__)

unique_id = os.getenv("UNIQUE_ID", "").replace(".", "-").replace("/", "-")
test_dataset = OptimizationDataset(
    name=f"AWS cifar10 classification dataset{unique_id}",
    labelling_type=LabellingType.SingleLabelClassification,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name=f"cifar10bucket{unique_id}",
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
    full_run = dataset_optimization_sync_test(
        test_dataset, "RUN_CLASSIFICATION_AWS_OPTIMIZATION"
    )
    if full_run:
        pass
        # TODO: Add add assertion for result
    else:
        logger.info("Full dataset optimization was not run!")
    cleanup(test_dataset)
