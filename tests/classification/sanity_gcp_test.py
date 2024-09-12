import json
import logging
import os

import pytest
from hirundo import (
    LabellingType,
    OptimizationDataset,
    StorageGCP,
    StorageIntegration,
    StorageLink,
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
    name=f"TEST-GCP sanity dataset{unique_id}",
    labelling_type=LabellingType.SingleLabelClassification,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name=f"cifar1bucket{unique_id}",
            type=StorageTypes.GCP,
            gcp=StorageGCP(
                bucket_name="cifar1bucket",
                project="Hirundo-global",
                credentials_json=json.loads(os.environ["GCP_CREDENTIALS"]),
            ),
        ),
        path="/pytorch-cifar/data",
    ),
    dataset_metadata_path="cifar1.csv",
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
        test_dataset,
        sanity=True,
        alternative_env="RUN_CLASSIFICATION_GCP_SANITY_OPTIMIZATION",
    )
    if full_run is not None:
        assert full_run.warnings_and_errors.size == 0
        assert full_run.suspects.size == 5000
        # TODO: Add more assertions for results
    else:
        logger.info("Full dataset optimization was not run!")


@pytest.mark.asyncio
async def test_async_dataset_optimization():
    await dataset_optimization_async_test(
        test_dataset, "RUN_CLASSIFICATION_GCP_SANITY_OPTIMIZATION"
    )
