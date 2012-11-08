
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
	rm -f `find . -name '*.pyc'`
	make -C libuv  clean

distclean: clean

##############################
# redistribution
##############################

redist: dist

.PHONY: dist
dist:
	@echo ">>> Making redistributable package..."
	$(PYTHON) setup.py bdist
	@echo ">>> redistributable package left in dist/"

