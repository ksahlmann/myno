
The namespace identified by the URI https://www.cs.uni-potsdam.de/bs/research/myno# is defined by the Research Group at the University Potsdam, Institute of Computer Science. This repository will contain resources related to this namespace and should be regarded as an experimental research.

# MYNO: MQTT-YANG-NETCONF-Ontology
We develope an architecture for network management of IoT devices in the Internet of Things (IoT). We use standards MQTT, YANG and NETCONF. The IoT device descriptions are based on the oneM2M Base Ontology.

# MQTT-NETCONF Bridge
The bridge is mapping between NETCONF RPCs and MQTT publish messages. It is parsing the ontology-based device descriptions tom the YANG, the data modelling language for the NETCONF. The implementation of the bridge is in the folder *myno-bridge*. 

## Status for Virtual Devices
We provide the current state of the ontology for Virtual Device in the folder *vd-ontology*. 

## Status for MYNO Update Protocol
The implementation of the MUP is in the folder *myno-update-protocol*.

The device application is in subfolder *CC2538-app*. The device is sending a Device-Token, validate the Manifest and receive the Update-Image.
For implementation details of CC2538EM see also https://github.com/contiki-os/contiki/tree/master/platform/cc2538dk

The MUP ontology is in subfolder *mup-ontology*.

The web-based Update Server is in subfolder *update-server*. 

The subfolder *tools* contains different tools: 

1. <u>micro-ecc-signature</u> is used for creation of signatures and keys. 
2. <u>compress-image</u> script is used to compress the update image file. 
3. <u>rdflib-jsonld</u> is the python library with a bugfix for namespaces with #. 


### License
This project is licensed under the terms of the GNU GPLv3 License.

