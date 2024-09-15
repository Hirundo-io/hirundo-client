import logging
import os

import pytest
from hirundo import (
    LabellingType,
    OptimizationDataset,
    StorageIntegration,
    StorageS3,
    StorageTypes,
)
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_async_test,
    dataset_optimization_sync_test,
    get_unique_id,
)

logger = logging.getLogger(__name__)

unique_id = get_unique_id()
test_dataset = OptimizationDataset(
    name=f"TEST-AWS-BDD-100k-subset-1000-OD-dataset{unique_id}",
    labelling_type=LabellingType.ObjectDetection,
    storage_integration=StorageIntegration(
        name=f"AWS-open-source-datasets-sanity{unique_id}",
        type=StorageTypes.S3,
        s3=StorageS3(
            bucket_url="s3://hirundo-open-source-datasets",
            region_name="il-central-1",
            access_key_id=os.environ["AWS_ACCESS_KEY"],
            secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        ),
    ),
    root="/bdd100k_subset_1000_hirundo.zip/bdd100k",
    dataset_metadata_path="bdd100k.csv",
    classes=[
        "traffic light",
        "traffic sign",
        "car",
        "pedestrian",
        "bus",
        "truck",
        "rider",
        "bicycle",
        "motorcycle",
        "train",
        "other vehicle",
        "other person",
        "trailer",
    ],
)


@pytest.fixture(autouse=True)
def cleanup_tests():
    cleanup(test_dataset, unique_id)
    yield
    cleanup(test_dataset, unique_id)


def test_dataset_optimization():
    full_run = dataset_optimization_sync_test(
        test_dataset, sanity=True, alternative_env="RUN_OD_AWS_SANITY_OPTIMIZATION"
    )
    if full_run is not None:
        pass
        # TODO: Add add assertion for result
    else:
        logger.info("Full dataset optimization was not run!")


@pytest.mark.asyncio
async def test_async_dataset_optimization():
    await dataset_optimization_async_test(
        test_dataset, "RUN_AWS_OD_SANITY_OPTIMIZATION"
    )
