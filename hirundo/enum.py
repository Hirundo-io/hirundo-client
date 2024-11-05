from enum import Enum


class LabellingType(str, Enum):
    """
    Enum indicate what type of labelling is used for the given dataset.
    Supported types are:
    """

    SINGLE_LABEL_CLASSIFICATION = "SingleLabelClassification"
    OBJECT_DETECTION = "ObjectDetection"
    SPEECH_TO_TEXT = "SpeechToText"


class DatasetMetadataType(str, Enum):
    """
    Enum indicate what type of metadata is provided for the given dataset.
    Supported types are:
    """

    HIRUNDO_CSV = "HirundoCSV"
