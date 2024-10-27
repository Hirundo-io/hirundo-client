import logging
import os

import pytest
from hirundo import (
    HirundoCSV,
    LabelingType,
    OptimizationDataset,
    StorageIntegration,
    StorageS3,
    StorageTypes,
)
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_sync_test,
    get_unique_id,
)

logger = logging.getLogger(__name__)

unique_id = get_unique_id()
s3_bucket = StorageS3(
    bucket_url="s3://cifar10bucket",
    region_name="us-east-2",
    access_key_id=os.environ["AWS_ACCESS_KEY"],
    secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)
test_dataset = OptimizationDataset(
    name=f"TEST-AWS cifar10 classification dataset{unique_id}",
    labeling_type=LabelingType.SingleLabelClassification,
    storage_integration=StorageIntegration(
        name=f"cifar10bucket{unique_id}",
        type=StorageTypes.S3,
        s3=s3_bucket,
    ),
    labeling_info=HirundoCSV(
        csv_url=s3_bucket.get_url(path="/pytorch-cifar/data/cifar10.csv"),
    ),
    data_root_url=s3_bucket.get_url(path="/pytorch-cifar/data"),
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


@pytest.fixture(autouse=True)
def cleanup_tests():
    cleanup(test_dataset, unique_id)
    yield
    cleanup(test_dataset, unique_id)


def test_dataset_optimization():
    full_run = dataset_optimization_sync_test(
        test_dataset, "RUN_CLASSIFICATION_AWS_OPTIMIZATION"
    )
    if full_run is not None:
        assert full_run.warnings_and_errors.size == 0
        # TODO: Add more assertions for results
    else:
        logger.info("Full dataset optimization was not run!")
