# -*- coding: utf-8 -*-
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

requires = [
    'click==6.7',
    'requests==2.18.1',
    'Fabric3==1.13.1.post1',
    'Jinja2==2.9.6'
]
tests_require = ['pytest', 'pytest-cache', 'pytest-cov']


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name="ArmCLI",
    version='0.0.2',
    description="CLI tools dor docker swarm deployment",
    long_description="\n\n".join([open("README.md").read()]),
    license='MIT',
    author="Victor Aguilar C.",
    author_email="victor@xiberty.com",
    url="https://ArmCLI.readthedocs.org",
    packages=['arm'],
    install_requires=requires,
    entry_points={'console_scripts': [
        'arm = arm.cli:main']},
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython'],
    extras_require={'test': tests_require},
    cmdclass={'test': PyTest})
