import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    """
    Overrides setup "test" command, taken from here:
    http://pytest.org/latest/goodpractises.html
    """

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest

        errno = pytest.main([])
        sys.exit(errno)


setup(
    name='enaml-extensions',
    version='0.2.0',
    author='Gabriel Reis',
    author_email='gabrielcnr@gmail.com',
    description='Extra widgets and extensions for building UIs with Enaml',
    url='http://github.com/gabrielcnr/enaml-extensions',
    license='LGPL',
    keywords='enaml qt widgets extras extensions table qt-table ui gui',
    requires=['enaml'],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        # 'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Desktop Environment :: Window Managers',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Software Development :: Widget Sets',
    ],
    tests_requires=['pytest'],
    cmdclass={'test': PyTest},
)
