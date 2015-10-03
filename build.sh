#!/usr/bin/env bash

rm -rf build dist && \
mkdir build dist && \
virtualenv build/venv && \
build/venv/bin/pip install -r requirements.txt --install-option --install-lib=$PWD/build/venv/requirements && \
cd dc-mixer && \
zip -r9  ../build/dc-mixer.zip * -x '*.pyc' && \
cd .. && \
echo '#!/usr/bin/env python' | cat - ./build/dc-mixer.zip > ./build/dc-mixer && \
chmod +x ./build/dc-mixer && \
cp build/dc-mixer dist/dc-mixer && \
build/venv/bin/python ./dist/dc-mixer -h && \
git add dist/dc-mixer && \
git stage dist/dc-mixer