.. hirundo documentation master file, created by
   sphinx-quickstart on Sun Jul 21 10:18:47 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. meta::
   :http-equiv=Content-Security-Policy: default-src 'self', frame-ancestors 'none'

hirundo documentation
=====================

Welcome to the ``hirundo`` client library documentation.

This package is used to interface with Hirundo's platform.

Currently the only supported feature is a simple API to optimize your ML datasets.

Optimizing a dataset
--------------------

You do not need to share any of your code to optimize your dataset.

Currently ``hirundo`` supports the following dataset types:
   - (Multi-class) Classification datasets
   - Object Detection datasets

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
   - ``suggested_conf``: suggested label confidence

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
   - ``suggested_conf``: suggested object label confidence

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules
