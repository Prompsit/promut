#!/bin/bash
#
# USAGE postprocess.sh < input > output
#

sed -e 's/ //g;s/▁/ /g' \
	-e 's/^[[:space:]]*//'
