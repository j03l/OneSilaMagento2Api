import os
from pathlib import Path
from setuptools import setup, find_packages


LONG_DESCRIPTION_SRC = 'README.rst'


def read(file):
    with open(os.path.abspath(file), 'r', encoding='utf-8') as f:
        return f.read()


# Parse version
init = Path(__file__).parent.joinpath("magento", "__init__.py")
for line in init.read_text().split("\n"):
    if line.startswith("__version__ ="):
        break
version = line.split(" = ")[-1].strip('"')

setup(
    name='OneSilaMagento2Api',
    packages=find_packages(),
    version=version,
    license='MIT',
    description='Python Magento 2 REST API Wrapper - Forked and Enhanced by OneSila',
    long_description=read(LONG_DESCRIPTION_SRC) + "\n\nOriginal author: Adam Korn",
    long_description_content_type="text/x-rst; charset=UTF-8",
    author='2024 OneSila - Smart Enterprise Cockpit, Adam Korn',
    author_email='david@tweave.com',
    url='https://github.com/OneSila/OneSilaMagento2Api',
    download_url="https://github.com/OneSila/OneSilaMagento2Api/tarball/master",
    keywords=["magento", "magento-api", "python-magento", "python", "python3", "magento-python", "pymagento", "py-magento", "magento2", "magento-2", "magento2-api"],
    install_requires=["requests"]
)

