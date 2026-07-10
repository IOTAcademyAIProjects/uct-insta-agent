#!/bin/bash
cd /teamspace/studios/this_studio/uct-insta-agent
/home/zeus/miniconda3/envs/cloudspace/bin/python3 pipelines/post-with-caption.py "$1" "$2" "$3"
