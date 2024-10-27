from enum import Enum


class LabelingType(str, Enum):
    """
    Enum indicate what type of labeling is used for the given dataset.
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
    COCO = "COCO"
