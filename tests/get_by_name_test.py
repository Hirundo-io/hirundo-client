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
from tests.dataset_optimization_shared import get_unique_id

unique_id = get_unique_id()
storage_integration_name = f"T-cifar1bucket_get_by_name{unique_id}"
optimization_dataset_name = f"T-cifar1_get_by_name{unique_id}"

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
        name=storage_integration_name,
        type=StorageTypes.GCP,
        gcp=StorageGCP(
            bucket_name="cifar1bucket",
            project="Hirundo-global",
            credentials_json=json.loads(os.environ["GCP_CREDENTIALS"]),
        ),
    ).create(replace_if_exists=True)

    new_storage_integration = StorageIntegration.get_by_name(
        storage_integration_name, StorageTypes.GCP
    )

    assert new_storage_integration is not None
    assert new_storage_integration.gcp is not None
    storage_gcp = new_storage_integration.gcp

    OptimizationDataset(
        name=optimization_dataset_name,
        labelling_type=LabellingType.SingleLabelClassification,
        storage_integration_id=new_storage_integration.id,
        data_root_url=storage_gcp.get_url("/pytorch-cifar/data"),
        metadata_file_url=storage_gcp.get_url("/pytorch-cifar/data/cifar1.csv"),
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

    dataset = OptimizationDataset.get_by_name(optimization_dataset_name)
    assert dataset is not None
