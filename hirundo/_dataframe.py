has_pandas = False
has_polars = False

try:
    import pandas as pd

    has_pandas = True
except ImportError:
    pass

try:
    import polars as pl

    has_polars = True
except ImportError:
    pass

__all__ = ["has_polars", "has_pandas", "pd", "pl"]
