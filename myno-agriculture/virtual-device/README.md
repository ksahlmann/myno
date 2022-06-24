# Documentation of Virtual Device Implementation 

## install and start Mosquitto MQTT Broker
c:\Program Files (x86)\mosquitto\mosquitto.exe

necessary files to copy in the installation folder:
pthreadVC2.dll
libeay32.dll
ssleay32.dll

## install and run MQTT.fx as a GUI
connect to local Mosquitto and test publish/subscribe 

## Python Implementation 
https://git.tools.f4.htw-berlin.de/sahlmann/Ontology.git

c:\projects\Code-Git\Ontology\vd-python\

## Python Libraries and other Resources
Python Libraries from Github
c:\projects\Python-Git\

NETCONF-MQTT Bridge and Simulator
c:\projects\_Code-SVN\Lindemann\trunk\

## Namespace for Extended Ontology
https://www.cs.uni-potsdam.de/bs/research/myno#

New extended ontology 
c:\projects\Code-Git\Ontology\ontology\virtual-ontology.owl


## Ontology in Protege 

Property assertions for individuals are converted into annotations (internally annotation property added).
It happens because OWL is mapped to RDF. See https://www.w3.org/TR/owl2-mapping-to-rdf/#Axioms_that_Generate_a_Main_Triple and https://www.w3.org/TR/2012/REC-owl2-mapping-to-rdf-20121211/#Translation_of_Axioms_with_Annotations 

If the ontology is saved as OWL or Turtle(?) than annotation should disappear. 

(Phenomena in sensor-data: after the file was edited outside of Protege and afterwards reloaded in Protege, the object properties appeared in annotations window but not annotation triples were added to the file.)

## NETCONF Server

* use with python 3.6 or newer
* needed libraries: phao-mqtt, netconf, ncclient
* config @beginning of netconf_server.py
	* NC_PORT = 44555
	* NC_DEBUG = False
	* BROKER_ADDR = "192.168.0.1"
	* BROKER_PORT = 1883
	
* generate rsa private key (host.key) file with openssl (this worked only, not ssh-keygen). Must be "-----BEGIN RSA PRIVATE KEY-----" at the beginning 
C:\Users\sahlmann\Downloads\MQTT\openssl-1.0.2o-i386-win32\openssl.exe
Generate an RSA private key, of size 2048, and output it to a file named host.key: 
$ openssl genrsa -out host.key 2048
Extract the public key from the key pair, which can be used in a certificate:
$ openssl rsa -in host.key -outform PEM -pubout -out public.pem
* run with python3 netconf_server.py

## Web Interface 
adjust target_ip:
target_ip = '127.0.0.1'

Browser URL:
http://127.0.0.1:5000/


## Ontology Editor Mobi 

Installed under C:\projects\mobi-distribution-1.13.69\bin\start.bat
https://localhost:8443/mobi/index.html#/ontology-editor


## How it works

1. start Mosquitto MQTT BROKER
2. Start MQTT.fx and subscribe to "yang/config" Topic 
3. Run NETCONF-MQTT bridge as python: netconf_server.py (uses yang_generator.py) and wait
4. Run Virtual Device as python: vd-mqttclient.py (uses aggregat.py) 
5. Start Web-Interface 
6. Run simulator as python: simulator.py

=> check generated "vd-ontology.owl" file in the "ontology" subfolder
=> check generated "gen_yang.txt" file 

## Current State


