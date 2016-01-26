#!/usr/bin/python
import os, glob
from setuptools import setup, find_packages

setup(name="multipatch", version="1.0.0",
      description="Print git logs from multiple repositories.",
      long_description=open('README.rst').read(), license="MIT",
      author="James Webber", author_email="bunkerprivate@gmail.com",
      packages=find_packages(exclude=["tests", "tests.*"]),
      entry_points={
          'console_scripts': [
              'multipatch = multipatch.cli:main',
           ],
      },
      url="http://github.com/bnkr/multipatch",
      test_suite='tests')
