import ast
import re

from setuptools import setup

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('imapnotify/__init__.py', 'rb') as f:
  version = str(
      ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))

install_requires = ['pytest-runner>=2.0,<3', 'aioimaplib>=0.5.14,<1.0.0']

tests_require = install_requires + ['pytest', 'mock']

setup(
    name='imapnotify',
    version=version,
    url='',
    license='MIT',
    author='Alexandr Skurikhin',
    author_email='a@skurih.in',
    description='',
    long_description=open('README.md').read(),
    packages=['imapnotify'],
    include_package_data=True,
    install_requires=install_requires,
    tests_require=tests_require,
    entry_points={
        'console_scripts': [
            'pyimapnotify=imapnotify.cli:main',
        ],
    })
