from setuptools import setup
from Cython.Build import cythonize


setup(ext_modules=cythonize('taper_equations_cy.pyx'))

# cd logjacks_app/timber && python taper_setup.py build_ext --inplace