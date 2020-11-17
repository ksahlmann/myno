# MYNO-Device

The MYNO Device is implemented and tested for CC2538EM. Toolchain for Contiki-NG must be installed before. The guide is to find in repository: https://github.com/contiki-ng/contiki-ng/wiki/Platform-cc2538dk.

Installation: 

```bash
# for easy installation the script can be used 
bash build_upload.sh

# /dev/ttyUSB1 must be adjusted to the port of the device 
make WERROR=0 TARGET=cc2538dk PORT=/dev/ttyUSB1 mqtt-client.upload
```

For Debugging Output of the devices : 
```bash
# /dev/ttyUSB1 must be adjusted to the port of the device 
make WERROR=0 TARGET=cc2538dk PORT=/dev/ttyUSB1 login
```

The incoming messages and also the printf calls  will be dispalyed on the console. 
