import setuptools
import os

with open('requirements.txt', "r") as f:
    requirements = f.read().splitlines()

with open('test_requirements.txt', "r") as f:
    test_requirements = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='pyfy',
    version="0.0.3d",
    author='Omar Ryhan',
    author_email='omarryhan@gmail.com',
    license='MIT',
    description="Lightweight python wrapper for Spotify's web API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    tests_require=test_requirements,
    url='https://github.com/omarryhan/spyfy',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)