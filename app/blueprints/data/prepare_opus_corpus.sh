#!/bin/bash

CORPUS_URL=$1
OPUS_WORKDIR=$2
SRC_LANG=$3
TRG_LANG=$4
CORPUS_NAME=$5
TMP_LOG_FILE=$6
CORPUS_AUX_DIR=$7

echo "- corpus url: $CORPUS_URL" > $TMP_LOG_FILE
echo "- opus workdir: $OPUS_WORKDIR" >> $TMP_LOG_FILE
echo "- src lang : $SRC_LANG" >> $TMP_LOG_FILE
echo "- trg lang: $TRG_LANG" >> $TMP_LOG_FILE
echo "- corpus name: $CORPUS_NAME" >> $TMP_LOG_FILE
echo "---------" >> $TMP_LOG_FILE

ZIP_PATH="$SRC_LANG-$TRG_LANG.txt.zip"
#CORPUS_AUX_DIR="$OPUS_WORKDIR/$CORPUS_NAME"
PREPARED_CORPUS_DIR="prepared_corpus"

echo "- zip path: $ZIP_PATH" >> $TMP_LOG_FILE
echo "- corpus aux dir: $CORPUS_AUX_DIR" >> $TMP_LOG_FILE
echo "- corpus prepared dir: $PREPARED_CORPUS_DIR" >> $TMP_LOG_FILE
echo "---------" >> $TMP_LOG_FILE

# Remove previous tries at preparing the corpus if for example it failed before
# Create corpus work folder and the final prepared corpus folder
rm -rf $CORPUS_AUX_DIR
mkdir -p $CORPUS_AUX_DIR

# Go into work folder, download corpus and unzip it
cd $CORPUS_AUX_DIR
wget -q $CORPUS_URL
#unzip $ZIP_PATH
unzip *.zip

#SOURCE_FILE="$CORPUS_NAME.$SRC_LANG-$TRG_LANG.$SRC_LANG"
#TARGET_FILE="$CORPUS_NAME.$SRC_LANG-$TRG_LANG.$TRG_LANG"
SOURCE_FILE="$CORPUS_NAME.*.$SRC_LANG"
TARGET_FILE="$CORPUS_NAME.*.$TRG_LANG"

echo "- source file: $SOURCE_FILE" >> $TMP_LOG_FILE
echo "- target file: $TARGET_FILE" >> $TMP_LOG_FILE
echo "---------" >> $TMP_LOG_FILE

# Paste the source and target files, and shuffle out a number of samples
# If number of samples in corpus is less than specified shuffle amount,
# then just the shuffled corpus will be returned.
PASTED_CORPUS="pasted.$SRC_LANG-$TRG_LANG"
SHUFFLED_CORPUS="shuffled.$SRC_LANG-$TRG_LANG"

echo "- pasted corpus: $PASTED_CORPUS" >> $TMP_LOG_FILE
echo "- shuffled corpus: $SHUFFLED_CORPUS" >> $TMP_LOG_FILE
echo "---------" >> $TMP_LOG_FILE

paste $SOURCE_FILE $TARGET_FILE > $PASTED_CORPUS
shuf -n 2500000 $PASTED_CORPUS > $SHUFFLED_CORPUS

# Split the source and target columns from the shuffled corpus into the prepared corpus folder
# And delete all of the remaining files from the corpus work folder
FINAL_SOURCE_FILE="$PREPARED_CORPUS_DIR/$CORPUS_NAME.$SRC_LANG-$TRG_LANG.$SRC_LANG"
FINAL_TARGET_FILE="$PREPARED_CORPUS_DIR/$CORPUS_NAME.$SRC_LANG-$TRG_LANG.$TRG_LANG"

echo "- final source file: $FINAL_SOURCE_FILE" >> $TMP_LOG_FILE
echo "- final target file: $FINAL_TARGET_FILE" >> $TMP_LOG_FILE
echo "---------" >> $TMP_LOG_FILE

mkdir -p $PREPARED_CORPUS_DIR

cut -f 1 $SHUFFLED_CORPUS > $FINAL_SOURCE_FILE
cut -f 2 $SHUFFLED_CORPUS > $FINAL_TARGET_FILE
rm -f *
