import logging
import os

from hirundo import GitRepo, OptimizationDataset, StorageIntegration


logger = logging.getLogger(__name__)


def cleanup(test_dataset: OptimizationDataset):
    datasets = OptimizationDataset.list()
    dataset_ids = [
        dataset["id"] for dataset in datasets if dataset["name"] == test_dataset.name
    ]
    storage_integration_ids = [
        dataset["storage_link"]["storage_integration_id"]
        for dataset in datasets
        if dataset["name"] == test_dataset.name
    ]
    running_datasets = {
        dataset["id"]: dataset["run_id"]
        for dataset in datasets
        if (
            dataset["name"] == test_dataset.name
            and dataset["run_id"] is not None
            and ("completed" not in dataset or dataset["completed"] is None)
        )
    }
    if len(dataset_ids) > 0:
        logger.debug("Found %s optimization datasets, deleting them", len(dataset_ids))
        logger.debug("Note: If I am not the owner, I will not be able to delete them")
    for dataset_id in dataset_ids:
        try:
            if dataset_id in running_datasets:
                run_id = running_datasets[dataset_id]
                logger.debug("Cancelling optimization dataset with run ID %s", run_id)
                OptimizationDataset.cancel_by_id(run_id)
            OptimizationDataset.delete_by_id(dataset_id)
        except Exception as e:
            logger.warning(
                "Failed to delete optimization dataset with ID %s and exception %s",
                dataset_id,
                e,
            )
    storage_integrations = StorageIntegration.list()
    git_repo_ids = [
        integration["git"]["repo"]["id"]
        for integration in storage_integrations
        if integration["id"] in storage_integration_ids
        and integration["git"] is not None
        and integration["git"]["repo"] is not None
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
    for git_repo_id in git_repo_ids:
        try:
            GitRepo.delete_by_id(git_repo_id)
        except Exception as e:
            logger.warning(
                "Failed to delete git repo with ID %s and exception %s",
                git_repo_id,
                e,
            )
    # ⬆️ Delete all datasets and storage integrations from the server for the given user's default organization
    test_dataset.clean_ids()
    # ⬆️ Reset `dataset_id`, `storage_integration_id`, and `run_id` values on `test_dataset` to default value of `None`
    # This prevents errors due to ID links to deleted datasets, storage integrations and runs


def dataset_optimization_sync_test(
    test_dataset: OptimizationDataset, alternative_env: str | None = None
):
    logger.info("Sync: Finished cleanup")
    if os.getenv("FULL_TEST", "false") == "true" or (
        alternative_env and os.getenv(alternative_env, "false") == "true"
    ):
        run_id = test_dataset.run_optimization()
        logger.info("Sync: Started dataset optimization run with run ID %s", run_id)
        events_generator = test_dataset.check_run()
        logger.info("Sync: Checking run progress")
        last_event = {}
        while True:
            try:
                last_event = next(events_generator)
                assert last_event is not None
                logger.info("Sync: Run event %s", last_event)
                if last_event["state"] == "AWAITING MANUAL APPROVAL":
                    raise StopIteration("Currently we require manual approval")
            except StopIteration:
                break
        state = last_event["state"]
        result = last_event["result"]
        logger.info("Sync: Results %s", result)
        assert (
            state == "SUCCESS" or state == "AWAITING MANUAL APPROVAL"
        ), f"Optimization failed with state {state}"
        return result
    else:
        test_dataset.create()
        logger.info("Sync: Created dataset %s", test_dataset.name)
        return None


async def dataset_optimization_async_test(test_dataset: OptimizationDataset):
    logger.info("Async: Finished cleanup")
    run_id = test_dataset.run_optimization()
    logger.info("Async: Started dataset optimization run with run ID %s", run_id)
    events_generator = test_dataset.acheck_run()
    logger.info("Async: Checking run progress")
    last_event = {}
    async for last_event in events_generator:
        assert last_event is not None
        logger.info("Async: Run event %s", last_event)
        if last_event["state"] == "AWAITING_MANUAL_APPROVAL":
            # Currently we require manual approval
            break
    logger.info("Async: Results %s", last_event["result"])
    return last_event["state"], last_event["result"]