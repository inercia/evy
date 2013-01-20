#!/bin/sh

if [ ! -f $1 ] ; then
	echo "ERROR: needs a test to run"
	exit 1
fi

PYTHONPATH=.. pycallgraph  -i evy.*   $@

