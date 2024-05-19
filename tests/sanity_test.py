import logging
import pytest
from hirundo import (
    OptimizationDataset,
    LabellingType,
    StorageLink,
    StorageIntegration,
    StorageTypes,
    StorageS3,
)

logger = logging.getLogger(__name__)

test_dataset = OptimizationDataset(
    name="Test dataset",
    labelling_type=LabellingType.SingleLabelClassification,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name="cifar10bucket",
            type=StorageTypes.S3,
            s3=StorageS3(
                bucket_url="s3://cifar10bucket",
                region_name="us-east-2",
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


def cleanup():
    datasets = OptimizationDataset.list()
    dataset_ids = [dataset["id"] for dataset in datasets]
    if len(dataset_ids) > 0:
        logger.debug(
            "Found %s optimization datasets, deleting them", len(dataset_ids)
        )
        logger.debug("Note: If I am not the owner, I will not be able to delete them")
    for dataset_id in dataset_ids:
        try:
            OptimizationDataset.delete_by_id(dataset_id)
        except Exception as e:
            logger.warning("Failed to delete optimization dataset with ID %s and exception %s", dataset_id, e)
    storage_integrations = StorageIntegration.list()
    storage_integration_ids = [
        integration["id"] for integration in storage_integrations
    ]
    if len(storage_integration_ids) > 0:
        logger.debug(
            "Found %s storage integrations, deleting them", len(storage_integration_ids)
        )
        logger.debug("Note: If I am not the owner, I will not be able to delete them")
    for storage_integration_id in storage_integration_ids:
        try:
            StorageIntegration.delete_by_id(storage_integration_id)
        except Exception as e:
            logger.warning(
                "Failed to delete storage integration with ID %s and exception %s",
                storage_integration_id,
                e,
            )
    test_dataset.clean_ids()


def test_dataset_optimization():
    cleanup()
    logger.info("Sync: Finished cleanup")
    test_dataset.run_optimization()
    logger.info("Sync: Startup dataset optimization run")
    events_generator = test_dataset.check_run()
    logger.info("Sync: Checking run progress")
    last_event = None
    while True:
        try:
            event = next(events_generator)
            assert event is not None
            assert isinstance(event, str)
            logger.info("Sync: Run event %s", event)
        except StopIteration:
            break
    assert last_event['state'] == "SUCCESS"
    assert last_event['result'] is not None
    logger.info("Sync: Results %s", last_event['result'])


@pytest.mark.asyncio
async def test_async_dataset_optimization():
    cleanup()
    logger.info("Async: Finished cleanup")
    test_dataset.run_optimization()
    logger.info("Async: Startup dataset optimization run")
    events_generator = test_dataset.acheck_run()
    logger.info("Async: Checking run progress")
    async for event in events_generator:
        assert event is not None
        assert isinstance(event, str)
        logger.info("Async: Run event %s", event)
