from setuptools import setup, find_packages

setup(
    name='sort-cpp-includes',
    version='0.0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'sort-cpp-includes = sort_cpp_includes.sort_cpp_includes:main'
        ]
    }
)
