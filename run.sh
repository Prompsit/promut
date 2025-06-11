#!/bin/bash
FLAGS=
MODE=$1
PORT="${2:-5011}"
IMAGE="${3:-mutnmt_lukas:latest}"

if [ $MODE = "cuda" ]
then
	FLAGS="--gpus all"
fi

echo "Running MutNMT (mode: $MODE) with FLAGS=$FLAGS and IMAGE=$IMAGE on port $PORT"

docker run \
$FLAGS \
-d \
--name mutnmt_lukas \
-p $PORT:5011 \
-e DEBUG=1 \
-v $(pwd)/app:/opt/mutnmt/app \
-v $(pwd)/data:/opt/mutnmt/data \
$IMAGE