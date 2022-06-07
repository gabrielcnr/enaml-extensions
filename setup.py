from setuptools import setup, find_packages

with open('README.md', encoding='utf-8') as fp:
    long_description = fp.read()


setup(
    name='enaml-extensions',
    version='0.2.0',
    author='Gabriel Reis',
    author_email='gabrielcnr@gmail.com',
    description='Extra widgets and extensions for building UIs with Enaml',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='http://github.com/gabrielcnr/enaml-extensions',
    license='LGPL',
    keywords='enaml qt widgets extras extensions table qt-table ui gui',
    requires=['enaml'],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    data_files = [("", ["LICENSE"])],
    package_data={
        '': ['*.enaml'],
    },
    include_package_data=True,
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
        "qtpy",
        "numpy",
    ],
    extras_require={
        "testing": [
            "pytest",
            "pytest-mock",
            "pytest-qt",
        ]
    },    
    tests_requires=['pytest', 'pytest-mock', 'pytest-qt'],
)
