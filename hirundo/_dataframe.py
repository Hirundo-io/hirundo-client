has_pandas = False
has_polars = False

pd = None
pl = None
int32 = type[None]
float32 = type[None]
string = type[None]
#  ⬆️ These are just placeholders for the int32, float32 and string types
#    for when neither pandas nor polars are available

try:
    import numpy as np
    import pandas as pd

    has_pandas = True
    int32 = np.int32
    float32 = np.float32
    string = str
except ImportError:
    pass

try:
    import polars as pl
    import polars.datatypes as pl_datatypes

    has_polars = True
    int32 = pl_datatypes.Int32
    float32 = pl_datatypes.Float32
    string = pl_datatypes.String
except ImportError:
    pass


__all__ = [
    "has_polars",
    "has_pandas",
    "pd",
    "pl",
    "int32",
    "float32",
    "string",
]
