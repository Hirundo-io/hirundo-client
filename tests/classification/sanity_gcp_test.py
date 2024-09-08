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


def test_dataset_optimization():
    cleanup(test_dataset, unique_id)
    full_run = dataset_optimization_sync_test(
        test_dataset,
        sanity=True,
        alternative_env="RUN_CLASSIFICATION_GCP_SANITY_OPTIMIZATION",
    )
    if full_run is not None:
        pass
        # TODO: Add add assertion for result
    else:
        logger.info("Full dataset optimization was not run!")
    cleanup(test_dataset, unique_id)


@pytest.mark.asyncio
async def test_async_dataset_optimization():
    cleanup(test_dataset, unique_id)
    await dataset_optimization_async_test(
        test_dataset, "RUN_CLASSIFICATION_GCP_SANITY_OPTIMIZATION"
    )
    cleanup(test_dataset, unique_id)
