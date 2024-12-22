import typing
import zipfile
from pathlib import Path
from typing import IO

import numpy as np
import requests

from hirundo._dataframe import has_pandas, has_polars, pd, pl
from hirundo._timeouts import DOWNLOAD_READ_TIMEOUT
from hirundo.dataset_optimization_results import DatasetOptimizationResults
from hirundo.logger import get_logger

ZIP_FILE_CHUNK_SIZE = 50 * 1024 * 1024  # 50 MB

CUSTOMER_INTERCHANGE_DTYPES = {
    "image_path": str,
    "label_path": str,
    "segments_mask_path": str,
    "segment_id": np.int32,
    "label": str,
    "bbox_id": str,
    "xmin": np.float32,
    "ymin": np.float32,
    "xmax": np.float32,
    "ymax": np.float32,
    "suspect_level": np.float32,  # If exists, must be one of the values in the enum below
    "suggested_label": str,
    "suggested_label_conf": np.float32,
    "status": str,
    # ⬆️ If exists, must be one of the following:
    # NO_LABELS/MISSING_IMAGE/INVALID_IMAGE/INVALID_BBOX/INVALID_BBOX_SIZE/INVALID_SEG/INVALID_SEG_SIZE
}

logger = get_logger(__name__)


def _clean_df_index(df: "pd.DataFrame") -> "pd.DataFrame":
    """
    Clean the index of a DataFrame in case it has unnamed columns.

    Args:
        df (DataFrame): DataFrame to clean

    Returns:
        Cleaned Pandas DataFrame
    """
    index_cols = sorted(
        [col for col in df.columns if col.startswith("Unnamed")], reverse=True
    )
    if len(index_cols) > 0:
        df.set_index(index_cols.pop(), inplace=True)
        df.rename_axis(index=None, columns=None, inplace=True)
        if len(index_cols) > 0:
            df.drop(columns=index_cols, inplace=True)

    return df


def load_df(
    file: "typing.Union[str, IO[bytes]]",
) -> "typing.Union[pd.DataFrame, pl.DataFrame, None]":
    """
    Load a DataFrame from a CSV file.

    Args:
        file_name: The name of the CSV file to load.
        dtypes: The data types of the columns in the DataFrame.

    Returns:
        The loaded DataFrame or `None` if neither Polars nor Pandas is available.
    """
    if has_polars:
        return pl.read_csv(file, schema_overrides=CUSTOMER_INTERCHANGE_DTYPES)
    elif has_pandas:
        df = pd.read_csv(file, dtype=CUSTOMER_INTERCHANGE_DTYPES)
        return _clean_df_index(df)


def download_and_extract_zip(run_id: str, zip_url: str) -> DatasetOptimizationResults:
    """
    Download and extract the zip file from the given URL.

    Note: It will only extract the `mislabel_suspects.csv`
    and `warnings_and_errors.csv` files from the zip file.

    Args:
        run_id: The ID of the optimization run.
        zip_url: The URL of the zip file to download.

    Returns:
        The dataset optimization results object.
    """
    # Define the local file path
    cache_dir = Path.home() / ".hirundo" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_file_path = cache_dir / f"{run_id}.zip"

    # Stream the zip file download
    with requests.get(zip_url, timeout=DOWNLOAD_READ_TIMEOUT, stream=True) as r:
        r.raise_for_status()
        with open(zip_file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=ZIP_FILE_CHUNK_SIZE):
                f.write(chunk)
        logger.info("Successfully downloaded the result zip file for run ID %s", run_id)

        with zipfile.ZipFile(zip_file_path, "r") as z:
            # Extract suspects file
            try:
                with z.open("mislabel_suspects.csv") as suspects_file:
                    suspects_df = load_df(suspects_file)
                logger.debug(
                    "Successfully loaded mislabel suspects into DataFrame for run ID %s",
                    run_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to load mislabel suspects into DataFrame", exc_info=e
                )

            try:
                # Extract warnings_and_errors file
                with z.open("warnings_and_errors.csv") as warnings_file:
                    warnings_and_errors_df = load_df(warnings_file)
                logger.debug(
                    "Successfully loaded warnings and errors into DataFrame for run ID %s",
                    run_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to load warnings and errors into DataFrame", exc_info=e
                )

            return DatasetOptimizationResults(
                cached_zip_path=zip_file_path,
                suspects=suspects_df,
                warnings_and_errors=warnings_and_errors_df,
            )


def load_from_zip(
    zip_path: Path, file_name: str
) -> "typing.Union[pd.DataFrame, pl.DataFrame, None]":
    """
    Load a given file from a given zip file.

    Args:
        zip_path: The path to the zip file.
        file_name: The name of the file to load.

    Returns:
        The loaded DataFrame or `None` if neither Polars nor Pandas is available.
    """
    with zipfile.ZipFile(zip_path, "r") as z:
        try:
            with z.open(file_name) as file:
                return load_df(file)
        except Exception as e:
            logger.error("Failed to load %s from zip file", file_name, exc_info=e)
    return None
