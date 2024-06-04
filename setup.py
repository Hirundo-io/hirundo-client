from setuptools import setup, find_packages

with open("requirements.txt", "r") as f:
    pip_requirements = f.read().splitlines()

with open("README.md", "r") as f:
    long_description = f.read()
setup(
    name="hirundo_client",
    version="0.1.0",
    packages=find_packages(),
    package_data={"hirundo": ["py.typed"]},
    install_requires=[pip_requirements],
    author="Hirundo",
    author_email="dev@hirundo.io",
    description="This package is used to interface with Hirundo's platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Hirundo-io/hirundo-client",
    license="MIT",
    entry_points={
        "console_scripts": ["hirundo=hirundo.cli:app"],
    },
)
