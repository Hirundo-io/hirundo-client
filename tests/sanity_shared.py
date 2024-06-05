import logging

from hirundo import OptimizationDataset
from hirundo.storage import StorageIntegration


logger = logging.getLogger(__name__)


def cleanup(test_dataset: OptimizationDataset):
    datasets = OptimizationDataset.list()
    dataset_ids = [dataset["id"] for dataset in datasets]
    if len(dataset_ids) > 0:
        logger.debug("Found %s optimization datasets, deleting them", len(dataset_ids))
        logger.debug("Note: If I am not the owner, I will not be able to delete them")
    for dataset_id in dataset_ids:
        try:
            OptimizationDataset.delete_by_id(dataset_id)
        except Exception as e:
            logger.warning(
                "Failed to delete optimization dataset with ID %s and exception %s",
                dataset_id,
                e,
            )
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
    # ⬆️ Delete all datasets and storage integrations from the server for the given user's default organization
    test_dataset.clean_ids()
    # ⬆️ Reset `dataset_id`, `storage_integration_id`, and `run_id` values on `test_dataset` to default value of `None`
    # This prevents errors due to ID links to deleted datasets, storage integrations and runs


def dataset_optimization_sync_test(test_dataset: OptimizationDataset):
    logger.info("Sync: Finished cleanup")
    test_dataset.run_optimization()
    logger.info("Sync: Started dataset optimization run")
    events_generator = test_dataset.check_run()
    logger.info("Sync: Checking run progress")
    last_event = {}
    while True:
        try:
            last_event = next(events_generator)
            assert last_event is not None
            assert isinstance(last_event, str)
            logger.info("Sync: Run event %s", last_event)
        except StopIteration:
            break
    assert last_event["state"] == "SUCCESS"
    assert last_event["result"] is not None
    logger.info("Sync: Results %s", last_event["result"])

async def dataset_optimization_async_test(test_dataset: OptimizationDataset):
    logger.info("Async: Finished cleanup")
    test_dataset.run_optimization()
    logger.info("Async: Started dataset optimization run")
    events_generator = test_dataset.acheck_run()
    logger.info("Async: Checking run progress")
    last_event = {}
    async for last_event in events_generator:
        assert last_event is not None
        assert isinstance(last_event, str)
        logger.info("Async: Run event %s", last_event)
    assert last_event["state"] == "SUCCESS"
    assert last_event["result"] is not None
    logger.info("Async: Results %s", last_event["result"])
