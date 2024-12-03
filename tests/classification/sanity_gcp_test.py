import json
import logging
import os

import pytest
from hirundo import (
    HirundoCSV,
    LabelingType,
    OptimizationDataset,
    StorageConfig,
    StorageGCP,
    StorageTypes,
)
from hirundo.dataset_optimization import AugmentationNames
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_async_test,
    dataset_optimization_sync_test,
    get_unique_id,
)

logger = logging.getLogger(__name__)

unique_id = get_unique_id()
gcp_bucket = StorageGCP(
    bucket_name="cifar1bucket",
    project="Hirundo-global",
    credentials_json=json.loads(os.environ["GCP_CREDENTIALS"]),
)
test_dataset = OptimizationDataset(
    name=f"TEST-GCP sanity dataset{unique_id}",
    labeling_type=LabelingType.SINGLE_LABEL_CLASSIFICATION,
    storage_config=StorageConfig(
        name=f"cifar1bucket{unique_id}",
        type=StorageTypes.GCP,
        gcp=gcp_bucket,
    ),
    labeling_info=HirundoCSV(
        csv_url=gcp_bucket.get_url(path="/pytorch-cifar/data/cifar1.csv"),
    ),
    data_root_url=gcp_bucket.get_url(path="/pytorch-cifar/data"),
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
    augmentations=[
        AugmentationNames.RandomHorizontalFlip,
        AugmentationNames.RandomVerticalFlip,
        AugmentationNames.ColorJitter,
    ],
)


@pytest.fixture(autouse=True)
def cleanup_tests():
    cleanup(test_dataset)
    yield
    cleanup(test_dataset)


def test_dataset_optimization():
    full_run = dataset_optimization_sync_test(
        test_dataset,
        sanity=True,
        alternative_env="RUN_CLASSIFICATION_GCP_SANITY_OPTIMIZATION",
    )
    if full_run is not None:
        assert full_run.warnings_and_errors.size == 0
        assert full_run.suspects.size >= 30_000
        # TODO: Add more assertions for results
    else:
        logger.info("Full dataset optimization was not run!")


@pytest.mark.asyncio
async def test_async_dataset_optimization():
    await dataset_optimization_async_test(
        test_dataset, "RUN_CLASSIFICATION_GCP_SANITY_OPTIMIZATION"
    )
