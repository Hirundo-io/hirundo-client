has_pandas = False
has_polars = False

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


__all__ = ["has_polars", "has_pandas", "pd", "pl", "int32", "float32", "string"]
