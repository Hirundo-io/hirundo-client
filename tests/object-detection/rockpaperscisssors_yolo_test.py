import json
import logging
import os

import pytest
from hirundo import (
    YOLO,
    LabelingType,
    OptimizationDataset,
    StorageConfig,
    StorageGCP,
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
gcp_bucket = StorageGCP(
    bucket_name="rock-paper-scissors-yolo",
    project="Hirundo-global",
    credentials_json=json.loads(os.environ["GCP_CREDENTIALS"]),
)
test_dataset = OptimizationDataset(
    name=f"TEST-GCP sanity YOLO dataset{unique_id}",
    labeling_type=LabelingType.OBJECT_DETECTION,
    storage_config=StorageConfig(
        name=f"rock-paper-scissors-yolo-{unique_id}",
        type=StorageTypes.GCP,
        gcp=gcp_bucket,
    ),
    labeling_info=YOLO(
        data_yaml_url=gcp_bucket.get_url(
            path="/Rock Paper Scissors SXSW.v14i.yolov8.zip/Rock Paper Scissors SXSW.v14i.yolov8/train/images/"
        ),
        labels_dir_url=gcp_bucket.get_url(
            path="/Rock Paper Scissors SXSW.v14i.yolov8.zip/Rock Paper Scissors SXSW.v14i.yolov8/train/labels/"
        ),
    ),
    data_root_url=gcp_bucket.get_url(
        path="/Rock Paper Scissors SXSW.v14i.yolov8.zip/Rock Paper Scissors SXSW.v14i.yolov8/data.yaml"
    ),
)


@pytest.fixture(autouse=True)
def cleanup_tests():
    cleanup(test_dataset)
    yield
    cleanup(test_dataset)


def test_dataset_optimization():
    full_run = dataset_optimization_sync_test(
        test_dataset,
        alternative_env="RUN_YOLO_OD_GCP_SANITY_OPTIMIZATION",
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
        test_dataset, "RUN_YOLO_OD_GCP_SANITY_OPTIMIZATION"
    )
