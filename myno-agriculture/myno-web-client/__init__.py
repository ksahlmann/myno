#!/usr/bin/bash
# -*- coding: utf-8 -*-

from flask import Flask, render_template, jsonify, url_for, request
from flask import Markup
from flask_mqtt import Mqtt

from threading import Thread

from getcaller import get_devices

import constants

from ncclient import manager
from ncclient import xml_ 

from lxml import etree		#needed because ncclient sends lxml, not xml object

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring

import threading

import logging 	#not really needed but silences ajax logs (occurring once per second per client) 
				#see variable suppress_werkzeugs_logs 

from socket import error as socket_error



app = Flask(__name__)

html_template_file = 'interface.html'

target_ip = '127.0.0.1'
target_ip = 'localhost'
target_port = 44555
target_username = 'user'
target_password = 'admin'

app.config['MQTT_BROKER_URL'] = target_ip
app.config['MQTT_BROKER_PORT'] = 1883
# for auth, config is ['MQTT_USERNAME'] and ['MQTT_PASSWORD']
app.config['MQTT_REFRESH_TIME'] = 1.0 


device_dict={}
sensor_dict={}

script_root=''

script_error=""
event_notification=""
event_notification_old="will get overwritten after first notification"
event_notification_counter=0
rpc_notification=""
rpc_notification_old="will get overwritten after first notification"
rpc_notification_counter=0
script_notification=""
script_notification_old="will get overwritten after first notification"
script_notification_counter=0



suppress_werkzeugs_logs = True

#silencing werkzeug logs
if(suppress_werkzeugs_logs):
	log = logging.getLogger('werkzeug')
	log.setLevel(logging.ERROR)
	
	
#gets called when user visits website, also used for "get devices"-button click
@app.route("/", methods=['POST','GET'])
def root():
	global script_root #needed for ajax.js
	script_root = url_for('root', _external=True)
	clear_data()
	
	if ('m' in globals() and m.connected): 	#checks for existing manager (NETCONF connection) to get devices
		get_device_dict()
	else:					#(re)connects if not connected to NETCONF Server 
		async_establish_manager_connection()
		
	return render_template(html_template_file, things_list=list_things(), errors=script_error);



#ajax used for errors, notifications, and providing sensor data
@app.route('/ajax', methods= ['GET'])
def ajax():
	global script_notification
	global script_notification_old
	global script_notification_counter
	global rpc_notification
	global rpc_notification_old
	global rpc_notification_counter
	global event_notification
	global event_notification_old
	global event_notification_counter


    #used for making notification disappear after a while
	if(script_notification_old==script_notification):
		script_notification_counter+=1
	if(script_notification_counter>8):
		script_notification=""
		script_notification_counter=0
	script_notification_old=script_notification

	# used for making notification disappear after a while
	if (rpc_notification_old == rpc_notification):
		rpc_notification_counter += 1
	if (rpc_notification_counter > 16):
		rpc_notification = ""
		rpc_notification_counter = 0
	rpc_notification_old = rpc_notification
	# used for making notification disappear after a while
	if (event_notification_old == event_notification):
		event_notification_counter += 1
	if (event_notification_counter > 8):
		event_notification = ""
		event_notification_counter = 0
	event_notification_old = event_notification
	return jsonify(error=script_error, notification=script_notification, sensors=sensor_dict, events=event_notification,selected_rpc=rpc_notification)


#user clicked an rpc button
@app.route('/function_call/<thing>/<function>',defaults={'param_type' : None,'param_name': None, 'value': None},methods=['GET', 'POST'])
@app.route('/function_call/<thing>/<function>/<param_type>/<param_name>/<value>',methods=['GET', 'POST'])
@app.route('/function_call/<thing>/<function>/<param_name>',methods=['GET', 'POST'])
#@app.route('/function_call/<thing>/<function>/<param_type>/<param_name>/>',defaults={'value': None},methods=['GET','POST'])
#@app.route('/function_call/<thing>/<function>',methods=['GET', 'POST'])

def function_click(thing, function, param_type, param_name, value):
	clear_ajax()
	global rpc_notification

	n = xml_.to_ele('<'+function+'/>')			#NETCONF expects data in form of XML
	child = etree.SubElement(n, "uuidInput")
	child.text = thing
	if(param_type == 'union'):
		parameters = value.split(";")
		value = ""
		del parameters[-1]
		#if request.method == 'POST':
		for parameter in parameters:
			value = value + request.form[parameter] + ","
		value = value[:-1]
	if (param_type == 'enumeration'):
		parameters = value.split(";")
		value = ""
		del parameters[-1]
		# if request.method == 'POST':
		for parameter in parameters:
			value = value + request.form[parameter] + ","
		value = value[:-1]
	# automation so far only differentiated by name
	if ("Auto" in function):
		parameters = value.split(";")
		value = ""
		del parameters[-1]
		for key, val in request.form.items():
			if (key == 'command' and val.split(",")[1] !='union'):
				# drop 'union' field
				value = value + val.split(",")[0] + ","
				break
			elif (key == 'command' and val.split(",")[1] == 'union'):
				# parameters are separated by comma (board behavior), however,
				# RGB inputs are also separated by comma, change to ':'
				value = value + val.split(",")[0] + ":"
			elif ("input" in key and "input_" not in key):
				value = value + val + ":"
			else:
				value = value + val + ","
		value = value[:-1]

	if(value!=None):#if parameter value, add xml-node
		child = etree.SubElement(n, param_name)
		child.text = value
	else:							
		value = ""
				
	print("Request:")
	print(xml_.to_xml(n,pretty_print=True))
	
	t = Thread(target=rpc_call, args=(n,)) 	#async because it can take a while
	t.start()								#and we don't want to block the main thread

	rpc_notification = (constants.make_rpc_info(thing,function,value) )
	return render_template(html_template_file, things_list=list_things(),errors=script_error)
	#selected_rpc_text= Markup(constants.make_rpc_info(thing,function,value)), errors=script_error)


#generating and sending the actual call
def rpc_call(n):
	global script_notification
	try:
		rpc_reply = m.dispatch(n) 							#dispatches the request
		print(str(rpc_reply))
		rpc_reply_xml_root = ET.fromstring(str(rpc_reply))	#gets reply to put it in notification
		for data_node in rpc_reply_xml_root.findall('./data'):
			for retval_node in data_node.findall('./retval'):
				print(retval_node.text)
				script_notification = constants.rpc_notification_text(retval_node.text)
	except Exception as e:
		set_script_error("request error, connection still active? Netconf still running? Log: "+str(e))
		print(script_error)


def get_device_dict():
	global m
	global device_dict
	
	try:	
		device_dict = get_devices(m) #imported from namespaceparser.py
		print("DEVICE DICT: " + str(device_dict))
	except (NameError, Exception ) as ee:
		if(ee.__class__.__name__=="NameError"):
			set_script_error('exception in get_devices(). '
			+ 'Probably manager not connected. '+'Log: '+str(ee))
		else:
			set_script_error('exception in get_devices(). Log: '+str(ee)) + ee
		print(script_error)


#iterates through device_dict, creates HTML-UI based on the contents of it + subscribes to mqtt
def list_things(): 
	content=''
	if(device_dict.items()):
		dictionary_length = len(device_dict)
		dictionary_position = 0
		for device_uuid, dict_value in sorted(device_dict.items()):
			dictionary_position += 1
			#thing's name and ID as header for each thing "section"
			content = content + constants.make_thing_text(dict_value[0]);
			content = content + constants.make_thing_id_text(device_uuid);
			
			#RPCs, are going to be buttons
			functions = dict_value[1]['rpcs']

			if (functions):#key: 	rpc name (displayed+called)
				#hasRPCs = True
				for key, value in sorted(functions.items()): 	#value: array of:
															#0 description (displayed on hover)
															#1 possible parameter leaf name
															#2 possible parameters to pass
					if(value[2] == 'union' and 'Conf' not in key):
						content = content + constants.make_parameter_form(device_uuid, key, value[0],value[1],value[2],value[3])
					elif(value[2] == 'enumeration' and 'Conf' in key): #enumeration
						content = content + constants.make_event_form(device_uuid, key, value[0], value[1],value[2], value[3])
					elif(value[2] and "Auto" in key):
						content = content + constants.make_automation_form(device_uuid, functions, key,value[0], value[1], value[2],value[3])
					elif(value[2] and "Update" in key):
						content = content + constants.make_manifest_form(device_uuid, key, value[0], value[1],value[2], value[3])
					elif(value[2]):# or empty #if RPC parameters contains parameters to pass
						content = content + constants.make_parameter_button(device_uuid, key, value[0], value[1], value[2],value[3])
					else:
						content = content + constants.make_function_button(device_uuid, key, value[0])

			#sensor data, going to be text fields updated by ajax.js
			sensors = dict_value[1]['sensors']
			# After Update for units: sensor dict has an array as values: array[0] is the mqtt topic
			# array[1] is the OM-2 unit name, which gets converted in constants.py
			if (sensors):
				content = content + constants.make_linebreak()
				for (key_sensor, value_sensor) in sorted(sensors.items()):
					if('Ev' in key_sensor):
						content = content + constants.make_sensor_event(key_sensor, value_sensor)
					else:
						content = content + constants.make_sensor_tf(key_sensor, value_sensor)

					if(mqtt):
						mqtt.subscribe(value_sensor[0])
					else:
						setup_mqtt()
						mqtt.subscribe(value_sensor[0])
			if(dictionary_position < dictionary_length):
				content = content + constants.make_hline()
		
	else:
		content = constants.make_linebreak() \
		+ constants.make_thing_id_text("No devices available, press \"Get Devices\" to refresh.")
			
	return Markup(content);


def async_establish_manager_connection():
	threading.Thread(target=establish_manager_connection).start()

#connects to NETCONF server via manager
def establish_manager_connection():
	global m
	try:
		m = manager.connect_ssh(target_ip, port=target_port, username=target_username,
		password=target_password,allow_agent=False,hostkey_verify=False,look_for_keys=False)
		
		get_device_dict()
		
	except socket_error as serr:
		set_script_error('socket_error exception in establish_manager_connection(). '
		+ 'Maybe unable to open socket. '+'Log: '+str(serr))
		print("establish_manager_connection(): Error socket_error couldnt open")
		print(serr)
	except Exception as e:
		set_script_error('exception in establish_manager_connection(). '+'Log: '+str(e))
		print("establish_manager_connection():  Exception something else not caught by socket_error")
		print(e)
		
#mqtt for receiving sensor values
def setup_mqtt():
	global mqtt
	mqtt = Mqtt(app)
	@mqtt.on_message()
	def handle_mqtt_message(client, userdata, message):
		global event_notification
		if message.topic.split("/")[0] == 'event':
			#if message.payload.decode() != "":
				#event_notification = constants.rpc_notification_text("Sensor: "+message.topic.split("/")[4]+"/"+message.topic.split("/")[3]+": "+message.payload.decode())
			sensor_dict[message.topic]=(message.payload.decode(), constants.get_timestamp() )
		else:
			sensor_dict[message.topic]=(message.payload.decode(), constants.get_timestamp() )
	#sensor_dict contains sensor values for each subscribed topic, gets queried at '/ajax' route


def set_script_error(error_string):
	global script_error
	script_error = error_string

		
def clear_data():
	clear_device_dict()
	clear_ajax()
	
def clear_device_dict():
	global device_dict
	device_dict.clear()
	sensor_dict.clear()
	
def clear_ajax():
	global script_error
	global rpc_notification
	global script_notification 
	global script_notification_counter
	global event_notification

	rpc_notification=''
	event_notification=''
	script_error=''
	script_notification=''
	script_notification_counter=0
	

if __name__ == "__main__":
	threading.Thread(target=setup_mqtt).start()	#MQTT client for sensor values
	async_establish_manager_connection()		#manager connection for scheme and RPCs
	app.run(debug=True, host='0.0.0.0')			#flask webserver launch







