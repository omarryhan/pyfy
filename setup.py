import setuptools

with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

with open("test_requirements.txt", "r") as f:
    test_requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyfy",
    version="1.2.3",
    author="Omar Ryhan",
    author_email="omarryhan@gmail.com",
    license="MIT",
    description="Sync/Async API wrapper for Spotify's web API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    tests_require=test_requirements,
    url="https://github.com/omarryhan/pyfy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
