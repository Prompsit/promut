#!/bin/bash
#
# USAGE preprocess.sh spmodel spmencode < input > output
#

SPMENCODE=$2

## simple pre-processing steps adapted from Moses tools

sed -e 's/，/,/g' \
    -e 's/。 */. /g' \
    -e 's/、/,/g' \
    -e 's/”/"/g' \
    -e 's/“/"/g' \
    -e 's/∶/:/g' \
    -e 's/：/:/g' \
    -e 's/？/\?/g' \
    -e 's/《/"/g' \
    -e 's/》/"/g' \
    -e 's/）/\)/g' \
    -e 's/！/\!/g' \
    -e 's/（/\(/g' \
    -e 's/；/;/g' \
    -e 's/１/"/g' \
    -e 's/」/"/g' \
    -e 's/「/"/g' \
    -e 's/０/0/g' \
    -e 's/３/3/g' \
    -e 's/２/2/g' \
    -e 's/５/5/g' \
    -e 's/６/6/g' \
    -e 's/９/9/g' \
    -e 's/７/7/g' \
    -e 's/８/8/g' \
    -e 's/４/4/g' \
    -e 's/． */. /g' \
    -e 's/～/\~/g' \
    -e "s/’/\'/g" \
    -e 's/…/\.\.\./g' \
    -e 's/━/\-/g' \
    -e 's/〈/\</g' \
    -e 's/〉/\>/g' \
    -e 's/【/\[/g' \
    -e 's/】/\]/g' \
    -e 's/％/\%/g' |
perl -C -pe 's/(?!\n)\p{C}/ /g;' |
sed 's/  */ /g;s/^ *//g;s/ *$//g' |
${SPMENCODE} --model $1

