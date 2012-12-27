
# the python interpreter
#PYTHON=python
PYTHON=pypy

# the libuv directory
LIBUV_DIR=libuv


##############################
# building
##############################

all: build

.PHONY: build
build: setup.py
	@echo ">>> Building up..."
	$(PYTHON) setup.py build

#$(LIBUV_DIR)/Makefile: checkout-submodule

checkout-submodule:
	@echo ">>> Checking out submodules..."
	git submodule init
	git submodule update

update-submodule:
	@echo ">>> Getting latests changes from submodules..."
	git submodule foreach git pull origin master

##############################
# testing
##############################

.PHONY: tests
tests: test
test:
	@echo ">>> Running all tests..."
	@PYTHONPATH=`pwd` nosetests -v

##############################
# cleaning
##############################

clean:
	@echo ">>> Cleaning up..."
	rm -rf build dist
	rm -rf *.egg-info __pycache__
	rm -rf Library
	rm -f `find . -name '*.pyc'`
	rm -rf `find . -name '__pycache__'`
	make -C libuv  clean
	make -C doc  clean

distclean: clean

##############################
# documentations
##############################

.PHONY: doc
doc: docs

docs: docs-html

docs-html: all
	@echo ">>> Making HTML documentation..."
	LANG=en_US.UTF-8  LC_ALL=en_US.UTF-8  make -C doc html

##############################
# redistribution
##############################

redist: dist

.PHONY: dist
dist:
	@echo ">>> Making redistributable package..."
	$(PYTHON) setup.py bdist
	@echo ">>> redistributable package left in dist/"

dist-debug: clean
	DISTUTILS_DEBUG=1 make dist

sdist:
	@echo ">>> Making redistributable sources package..."
	$(PYTHON) setup.py sdist
	@echo ">>> redistributable package left in dist/"

sdist-debug: clean
	DISTUTILS_DEBUG=1 make sdist

sdist-upload: sdist
	@echo ">>> Uploading redistributable sources package to PyPI..."
	$(PYTHON) setup.py sdist upload

sdist-register: sdist
	@echo ">>> Registering package at PyPI..."
	$(PYTHON) setup.py register
