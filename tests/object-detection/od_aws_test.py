import logging
import os
from hirundo import (
    OptimizationDataset,
    LabellingType,
    StorageLink,
    StorageIntegration,
    StorageS3,
    StorageTypes,
)
from tests.dataset_optimization_shared import (
    cleanup,
    dataset_optimization_sync_test,
)

logger = logging.getLogger(__name__)

unique_id = os.getenv("UNIQUE_ID", "").replace(".", "-")
test_dataset = OptimizationDataset(
    name=f"AWS-BDD-100k-validation-OD-dataset{unique_id}",
    labelling_type=LabellingType.ObjectDetection,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name=f"AWS-open-source-datasets{unique_id}",
            type=StorageTypes.S3,
            s3=StorageS3(
                bucket_url="s3://hirundo-open-source-datasets",
                region_name="il-central-1",
                access_key_id=os.environ["AWS_ACCESS_KEY"],
                secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            ),
        ),
        path="/bdd100k_val_hirundo.zip/bdd100k",
    ),
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


def test_dataset_optimization():
    cleanup(test_dataset)
    full_run = dataset_optimization_sync_test(test_dataset, "RUN_AWS_OD_OPTIMIZATION")
    if full_run:
        pass
        # TODO: Add add assertion for result
    else:
        logger.info("Full dataset optimization was not run!")
