# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages

BASE_DIR = os.path.realpath(os.path.dirname(__file__))


def generate_version():
    version = "1.0.0"
    if os.path.isfile(os.path.join(BASE_DIR, "version.txt")):
        with open("version.txt", "r") as fd:
            content = fd.read().strip()
            if content:
                version = content
    return version


def parse_requirements():
    reqs = []
    if os.path.isfile(os.path.join(BASE_DIR, "requirements.txt")):
        with open(os.path.join(BASE_DIR, "requirements.txt"), 'r') as fd:
            for line in fd.readlines():
                line = line.strip()
                if line:
                    reqs.append(line)
    return reqs


if __name__ == "__main__":

    setup(
      version=generate_version(),
      name="qt4s",
      cmdclass={},
      packages=find_packages(exclude=("tests", "tests.*",)),
      include_package_data=True,
      package_data={'':['*.txt', '*.TXT', '*.dll', '*.so', '*.pem', '*.pyd', '*.exe']},
      author="Tencent",
      author_email="t_QTA@tencent.com",
      license="Copyright(c)2010-2018 Tencent All Rights Reserved. ",
      install_requires=parse_requirements()
      )
