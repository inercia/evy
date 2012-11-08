
# the python interpreter
PYTHON=python

# the libuv directory
LIBUV_DIR=libuv


##############################
# building
##############################

all: build

.PHONY: build
build: setup.py setup_libuv.py $(LIBUV_DIR)/Makefile
	@echo ">>> Building up..."
	$(PYTHON) setup.py build

$(LIBUV_DIR)/Makefile: update-submodule

update-submodule:
	git submodule init
	git submodule update

##############################
# cleaning
##############################

clean:
	@echo ">>> Cleaning up..."
	rm -rf build dist
	rm -rf *.egg-info __pycache__
	rm -rf Library
	rm -rf doc/_build doc/__pycache__
	rm -f `find . -name '*.pyc'`
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

