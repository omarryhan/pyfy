import setuptools
import os
import pyfy

with open('requirements.txt', "r") as f:
    requirements = f.read().splitlines()

with open('test_requirements.txt', "r") as f:
    test_requirements = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name=pyfy.__name__,
    version=pyfy.__version__,
    author=pyfy.__author__,
    author_email=pyfy.__author_email__,
    license=pyfy.__license__,
    description=pyfy.__about__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    tests_require=test_requirements,
    url=pyfy.__url__,
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)