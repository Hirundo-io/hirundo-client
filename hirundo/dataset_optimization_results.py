import typing
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from hirundo._dataframe import pd, pl


class DatasetOptimizationResults(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    cached_zip_path: Path
    """
    The path to the cached zip file of the results
    """
    suspects: "typing.Union[pl.DataFrame, pd.DataFrame, None]"
    """
    A pandas DataFrame containing the results of the optimization run
    """
    warnings_and_errors: "typing.Union[pl.DataFrame, pd.DataFrame, None]"
    """
    A pandas DataFrame containing the warnings and errors of the optimization run
    """
