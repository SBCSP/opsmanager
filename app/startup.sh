#!/bin/bash
nohup python app.py > flask_app.log 2>&1 &
echo $! > flask_app.pid
