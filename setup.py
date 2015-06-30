from setuptools import setup, find_packages

setup(
    name='enaml-extensions',
    version='0.1.0',
    author='Gabriel Reis',
    author_email='gabrielcnr@gmail.com',
    description='Enaml extra widgets and extensions',
    license='LGPL',
    keywords='enaml qt widgets extras extensions',
    requires=['enaml'],
    packages=find_packages(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Desktop Environment :: Window Managers',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Software Development :: Widget Sets',
    ],
)