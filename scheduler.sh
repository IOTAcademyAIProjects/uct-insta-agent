#!/bin/bash
cd /teamspace/studios/this_studio/uct-insta-agent
/home/zeus/miniconda3/envs/cloudspace/bin/python3 pipelines/scheduler.py "$1" "$2" "$3" "$4"
