import json
import os

import pytest
from hirundo import (
    LabellingType,
    OptimizationDataset,
    StorageGCP,
    StorageIntegration,
    StorageTypes,
)

STORAGE_INTEGRATION_NAME = "T-cifar1bucket_get_by_name"
OPTIMIZATION_DATASET_NAME = "T-cifar1_get_by_name"

new_storage_integration = None
new_dataset = None


@pytest.fixture(autouse=True)
def cleanup_tests():
    yield
    if new_dataset:
        new_dataset.delete()
    if new_storage_integration:
        new_storage_integration.delete()


def test_get_by_name():
    StorageIntegration(
        name=STORAGE_INTEGRATION_NAME,
        type=StorageTypes.GCP,
        gcp=StorageGCP(
            bucket_name="cifar1bucket",
            project="Hirundo-global",
            credentials_json=json.loads(os.environ["GCP_CREDENTIALS"]),
        ),
    ).create(replace_if_exists=True)

    new_storage_integration = StorageIntegration.get_by_name(
        STORAGE_INTEGRATION_NAME, StorageTypes.GCP
    )

    assert new_storage_integration is not None

    OptimizationDataset(
        name=OPTIMIZATION_DATASET_NAME,
        labelling_type=LabellingType.SingleLabelClassification,
        storage_integration=new_storage_integration,
        root="/pytorch-cifar/data",
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
    ).create(replace_if_exists=True)

    dataset = OptimizationDataset.get_by_name(OPTIMIZATION_DATASET_NAME)
    assert dataset is not None
