all: setup


setup: setup.py
	python setup.py build


clean:
	rm -rf build
	rm -rf __pycache__
	rm -f `find . -name '*.pyc'`
	make -C libuv  clean