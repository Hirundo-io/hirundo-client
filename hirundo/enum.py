from enum import Enum


class LabellingType(str, Enum):
    SingleLabelClassification = "SingleLabelClassification"
    ObjectDetection = "ObjectDetection"


class DatasetMetadataType(str, Enum):
    HirundoCSV = "HirundoCSV"
    # TODO: Add support for COCO and YOLO