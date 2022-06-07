from setuptools import setup
from Cython.Build import cythonize


setup(ext_modules=cythonize('_taper_equations_cy.pyx'))

# to re-run cythonize in the terminal
# cd .../_cython && python taper_setup.py build_ext --inplace


# _taper_equations_cy.c will be within the _cython module
# copy _taper_equations_cy.cp310-win_amd64.pyd from build/lib.win-amd64-3.10/../../../cython into the _cython module