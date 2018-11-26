import os

from setuptools import find_packages, setup


def load_description():
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, "README.md")
    with open(filename, "r") as f:
        return f.read()


requirements = ["beem", "discord-webhook"]

setup(
    name="utbot",
    version="0.0.1",
    author="Martin Šmíd",
    author_email="martin.smid94@seznam.cz",
    packages=find_packages(),
    long_description=load_description(),
    long_description_type="text/markdown",
    url="https://github.com/espoem/utbot",
    install_requires=requirements,
)
