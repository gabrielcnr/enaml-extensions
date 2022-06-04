import sys

from setuptools import setup, find_packages


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
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Desktop Environment :: Window Managers',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Software Development :: Widget Sets',
    ],
    use_scm_version={"write_to": "src/enamlext/_version.py"},
    setup_requires=["setuptools-scm", "setuptools>=30.3.0"],    
    python_requires=">=3.8",
    install_requires=[
        "enaml",
        "QScintilla",
        "pip",
    ],
    extras_require={
        "testing": [
            "pytest",
            "pytest-mock",
        ]
    },    
    tests_requires=['pytest', 'pytest-mock'],
)
