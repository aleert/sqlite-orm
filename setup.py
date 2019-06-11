# -*- coding: utf-8 -*-
from io import open

from setuptools import find_packages, setup


def read(f):
    return open(f, 'r', encoding='utf-8').read()


setup(
    name='sqlite_orm',
    version=0.1,
    license='BSD',
    description='Small SQLite ORM.',
    long_description=read('README.rst'),
    long_description_content_type='text/markdown',
    author='Aleksei Panfilov',
    author_email='aleert@yandex.ru',
    packages=find_packages(exclude=['test']),
    include_package_data=True,
    install_requires=[

    ],
    python_requires='>=3.6',
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
    ],
)
