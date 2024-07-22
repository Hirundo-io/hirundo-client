from enum import Enum


class LabellingType(str, Enum):
    """
    Enum indicate what type of labelling is used for the given dataset.
    Supported types are:
    """

    SingleLabelClassification = "SingleLabelClassification"
    ObjectDetection = "ObjectDetection"


class DatasetMetadataType(str, Enum):
    """
    Enum indicate what type of metadata is provided for the given dataset.
    Supported types are:
    """

    HirundoCSV = "HirundoCSV"
