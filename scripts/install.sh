#!/bin/bash

#cd /tmp
#git clone https://github.com/google/sentencepiece.git
#cd sentencepiece
#mkdir build
#cd build
#cmake ..
#make -j $(nproc)
#make install
#ldconfig -v

cd /opt/mutnmt

git submodule update --init --recursive

npm install npm@latest -g
npm install postcss-cli autoprefixer sass postcss -g

source venv/bin/activate

python3 -c 'import nltk; nltk.download("punkt")'
python3 -c 'import nltk; nltk.download("punkt_tab")'

