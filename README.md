# Hirundo

This package exposes access to Hirundo APIs for dataset optimization for Machine Learning.

Dataset optimization is currently available for datasets labelled for classification and object detection.


Support dataset storage integrations include:
   - Google Cloud (GCP) Storage
   - Amazon Web Services (AWS) S3
   - Git LFS (Large File Storage) repositories (e.g. GitHub or HuggingFace)

Optimizing a classification dataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Currently ``hirundo`` requires a CSV file with the following columns (all columns are required):
   - ``image_path``: The location of the image within the dataset ``root``
   - ``label``: The label of the image, i.e. which the class that was annotated for this image

And outputs a CSV with the same columns and:
   - ``suspect_level``: mislabel suspect level
   - ``suggested_label``: suggested label
   - ``suggested_label_conf``: suggested label confidence

Optimizing an object detection (OD) dataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Currently ``hirundo`` requires a CSV file with the following columns (all columns are required):
   - ``image_path``: The location of the image within the dataset ``root``
   - ``bbox_id``: The index of the bounding box within the dataset. Used to indicate label suspects
   - ``label``: The label of the image, i.e. which the class that was annotated for this image
   - ``x1``, ``y1``, ``x2``, ``y2``: The bounding box coordinates of the object within the image

And outputs a CSV with the same columns and:
   - ``suspect_level``: object mislabel suspect level
   - ``suggested_label``: suggested object label
   - ``suggested_label_conf``: suggested object label confidence

Note: This Python package must be used alongside a Hirundo server, either the SaaS platform, a custom VPC deployment or an on-premises installation.


## Installation

You can install the codebase with a simple `pip install hirundo` to install the latest version of this package. If you prefer to install from the Git repository and/or need a specific version or branch, you can simply clone the repository, check out the relevant commit and then run `pip install .` to install that version. A full list of dependencies can be found in `requirements.txt`, but these will be installed automatically by either of these commands.

## Usage

Classification example:
```
from hirundo.dataset_optimization import OptimizationDataset
from hirundo.enum import LabellingType
from hirundo.storage import StorageIntegration, StorageLink, StorageTypes

test_dataset = OptimizationDataset(
    name="TEST-GCP cifar 100 classification dataset",
    labelling_type=LabellingType.SingleLabelClassification,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name="cifar100bucket",
            type=StorageTypes.GCP,
            gcp=StorageGCP(
                bucket_name="cifar100bucket",
                project="Hirundo-global",
                credentials_json=json.loads(os.environ["GCP_CREDENTIALS"]),
            ),
        ),
        path="/pytorch-cifar/data",
    ),
    dataset_metadata_path="cifar100.csv",
    classes=cifar100_classes,
)

test_dataset.run_optimization()
results = test_dataset.check_run()
print(results)
```


Object detection example:

```
from hirundo.dataset_optimization import OptimizationDataset
from hirundo.enum import LabellingType
from hirundo.storage import StorageIntegration, StorageLink, StorageTypes

test_dataset = OptimizationDataset(
    name=f"TEST-HuggingFace-BDD-100k-validation-OD-validation-dataset{unique_id}",
    labelling_type=LabellingType.ObjectDetection,
    dataset_storage=StorageLink(
        storage_integration=StorageIntegration(
            name=f"BDD-100k-validation-dataset{unique_id}",
            type=StorageTypes.GIT,
            git=StorageGit(
                repo=GitRepo(
                    name=f"BDD-100k-validation-dataset{unique_id}",
                    repository_url="https://git@hf.co/datasets/hirundo-io/bdd100k-validation-only",
                ),
                branch="main",
            ),
        ),
        path="/BDD100K Val from Hirundo.zip/bdd100k",
    ),
    dataset_metadata_path="bdd100k.csv",
)

test_dataset.run_optimization()
results = test_dataset.check_run()
print(results)
```

Note: Currently we only support the main CPython release 3.9, 3.10 and 3.11. PyPy support may be introduced in the future.

## Further documentation

To learn about mroe how to use this library, please visit the [http://docs.hirundo.io/](documentation) or see the Google Colab examples.
