#!/bin/bash
cd /teamspace/studios/this_studio/uct-insta-agent

ARGS=()
if [ -n "$1" ]; then
  ARGS+=("$1")
fi
if [ -n "$2" ]; then
  ARGS+=("$2")
fi

/home/zeus/miniconda3/envs/cloudspace/bin/python3 pipelines/get-analytics.py "${ARGS[@]}"
