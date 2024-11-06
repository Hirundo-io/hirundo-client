import os
import typing

from hirundo import (
    GitRepo,
    OptimizationDataset,
    RunArgs,
    StorageIntegration,
    StorageTypes,
)
from hirundo.dataset_optimization import RunStatus
from hirundo.logger import get_logger

logger = get_logger(__name__)


def get_unique_id():
    return (
        os.getenv("UNIQUE_ID", "").replace(".", "-").replace("/", "-").replace("+", "-")
    )


def log_cleanup(storage_integration_ids: list[int], git_repo_ids: list[int]):
    if len(storage_integration_ids) > 0:
        logger.debug(
            "Found %s storage integrations, deleting them", len(storage_integration_ids)
        )
        logger.debug("Note: If I am not the owner, I will not be able to delete them")
    if len(git_repo_ids) > 0:
        logger.debug("Found %s git repos, deleting them", len(git_repo_ids))
        logger.debug("Note: If I am not the owner, I will not be able to delete them")


def cleanup_conflict_by_unique_id(unique_id: typing.Optional[str]):
    if not unique_id:
        return
    conflicting_git_repo_ids = [
        git_repo.id for git_repo in GitRepo.list() if unique_id in git_repo.name
    ]
    for conflicting_git_repo_id in conflicting_git_repo_ids:
        try:
            GitRepo.delete_by_id(conflicting_git_repo_id)
        except Exception as e:
            logger.warning(
                "Failed to delete git repo with ID %s and exception %s",
                conflicting_git_repo_id,
                e,
            )
    conflicting_storage_integration_ids = [
        storage_integration.id
        for storage_integration in StorageIntegration.list()
        if unique_id in storage_integration.name and storage_integration.id is not None
    ]
    for conflicting_storage_integration_id in conflicting_storage_integration_ids:
        try:
            StorageIntegration.delete_by_id(conflicting_storage_integration_id)
        except Exception as e:
            logger.warning(
                "Failed to delete storage integration with ID %s and exception %s",
                conflicting_storage_integration_id,
                e,
            )


def cleanup(test_dataset: OptimizationDataset):
    logger.info("Started cleanup")
    datasets = OptimizationDataset.list()
    dataset_ids = [
        dataset.id
        for dataset in datasets
        if dataset.name == test_dataset.name and dataset.id
    ]
    storage_integration_ids = [
        dataset.storage_integration.id
        for dataset in datasets
        if dataset.name == test_dataset.name
        and dataset.storage_integration.id is not None
    ]
    running_datasets = {
        dataset.id: dataset.run_id
        for dataset in datasets
        if (
            dataset.name == test_dataset.name
            and dataset.run_id is not None
            and dataset.status == RunStatus.STARTED
        )
    }
    if len(dataset_ids) > 0:
        logger.debug(
            "Found %s optimization datasets with the same name, deleting them",
            len(dataset_ids),
        )
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
                "Unable to delete optimization dataset with ID %s and exception %s",
                dataset_id,
                e,
            )
    storage_integrations = StorageIntegration.list()
    storage_integration_ids = (
        [
            storage_integration.id
            for storage_integration in storage_integrations
            if storage_integration.name == test_dataset.storage_integration.name
        ]
        if (test_dataset.storage_integration is not None)
        else storage_integration_ids
    )  # ⬆️ If given a StorageIntegration object, use it's name to find the matching IDs
    git_repo_ids = [
        integration.git.repo.id
        for integration in storage_integrations
        if integration.type == StorageTypes.GIT and integration.git is not None
    ]
    log_cleanup(storage_integration_ids, git_repo_ids)
    for storage_integration_id in storage_integration_ids:
        try:
            StorageIntegration.delete_by_id(storage_integration_id)
        except Exception as e:
            logger.warning(
                "Unable to delete storage integration with ID %s and exception %s",
                storage_integration_id,
                e,
            )
    for git_repo_id in git_repo_ids:
        try:
            GitRepo.delete_by_id(git_repo_id)
        except Exception as e:
            logger.warning(
                "Unable to delete git repo with ID %s and exception %s",
                git_repo_id,
                e,
            )
    # ⬆️ Delete all datasets and storage integrations from the server for the given user's default organization
    test_dataset.clean_ids()
    # ⬆️ Reset `dataset_id`, `storage_integration_id`, and `run_id` values on `test_dataset` to default value of `None`
    # This prevents errors due to ID links to deleted datasets, storage integrations and runs
    logger.info("Finished cleanup")


def dataset_optimization_sync_test(
    test_dataset: OptimizationDataset,
    alternative_env: typing.Optional[str] = None,
    sanity=False,
    run_args: typing.Optional[RunArgs] = None,
):
    logger.info("Sync: Finished cleanup")
    if (os.getenv("FULL_TEST", "false") == "true" and sanity) or (
        alternative_env and os.getenv(alternative_env, "false") == "true"
    ):
        run_id = test_dataset.run_optimization(
            replace_if_exists=True, run_args=run_args
        )
        logger.info("Sync: Started dataset optimization run with run ID %s", run_id)
        logger.info("Sync: Checking run progress")
        result = test_dataset.check_run(stop_on_manual_approval=True)
        logger.info("Sync: Results %s", result)
        return result
    else:
        test_dataset.create(replace_if_exists=True)
        logger.info("Sync: Created dataset %s", test_dataset.name)
        return None


async def dataset_optimization_async_test(
    test_dataset: OptimizationDataset,
    env: str,
    run_args: typing.Optional[RunArgs] = None,
):
    logger.info("Async: Finished cleanup")
    if os.getenv(env, "false") == "true":
        run_id = test_dataset.run_optimization(
            replace_if_exists=True, run_args=run_args
        )
        logger.info("Async: Started dataset optimization run with run ID %s", run_id)
        events_generator = test_dataset.acheck_run()
        logger.info("Async: Checking run progress")
        last_event = {}
        async for last_event in events_generator:
            assert last_event is not None
            logger.info("Async: Run event %s", last_event)
            if last_event["state"] == RunStatus.AWAITING_MANUAL_APPROVAL:
                # Currently we require manual approval
                break
        logger.info("Async: Results %s", last_event["result"])
        return last_event["result"]
    else:
        test_dataset.create(replace_if_exists=True)
        logger.info("Async: Created dataset %s", test_dataset.name)
        return None
