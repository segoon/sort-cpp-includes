from setuptools import setup, find_packages

setup(
    name='sort-cpp-includes',
    version='0.0.1',
    packages=find_packages(),
    scripts=['./src/sort_cpp_includes/sort_cpp_includes.py'],
)
