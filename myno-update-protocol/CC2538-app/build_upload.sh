#!/bin/bash 
make WERROR=0 TARGET=cc2538dk PORT=/dev/ttyUSB1 mqtt-client.upload
