v.0.2
----------------RUN----------------
Edit IP address (and maybe auth) for NETCONF-Server and MQTT in __init__.py lines 35-42.
Runs with python 2.7 as well as 3.5, call 
	python __init__.py
to launch webserver. In your browser, navigate to 
	127.0.0.1:5000
to access web interface.

If necessary, check IMPORTS section.



--------------IMPORTS--------------
All of the following are available via pip.

	- flask
Used as webserver

will install the following:
Jinja2-2.8 MarkupSafe-0.23 Werkzeug click flask itsdangerous 
(653kB)


	- flask_mqtt
MQTT client for flask, used to receive sensor values

will install the following:
typing, paho-mqtt, flask-mqtt
(85kB)


	- ncclient
NETCONF client, used to connect to NETCONF server

will install the following:
setuptools, pycparser, cffi, six, pynacl, pyasn1, idna, asn1crypto, cryptography, 
bcrypt, paramiko, lxml, ncclient
(10,106kB)


	- pyang
YANG validator and converter, used to convert YANG to YIN (XML format)

will install the following:
pyang
(327kB)


