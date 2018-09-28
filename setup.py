import setuptools
import os

from twine import repository

current_dir = os.path.dirname(os.path.realpath(__file__))
join = os.path.join

with open('requirements/requirements.txt', "r") as f:
    requirements = f.read().splitlines()

with open('requirements/test_requirements.txt', "r") as f:
    test_requirements = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = requirements

tests_require = test_requirements

setuptools.setup(
    name="pyfy",
    version="0.0.1",
    author="Omar Ryhan",
    author_email="omarryhan@gmail.com",
    license="MIT",
    description="Lightweight python wrapper for Spotify's web API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requires,
    tests_require=tests_require,
    url="https://github.com/omarryhan/pyfy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)