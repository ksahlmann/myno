#!/usr/bin/bash
# -*- coding: utf-8 -*-
# Copyright (c) 2020, Michael Nowak, Vera Clemens
 
from flask import Flask, render_template, jsonify, url_for, request
from flask import Markup
from flask_mqtt import Mqtt
import time
from threading import Thread
import os
#import progressbar

from getcaller import get_devices, get_update_devices

import copy
import constants
import csv
import subprocess

from ncclient import manager
from ncclient import xml_ 

from lxml import etree		#needed because ncclient sends lxml, not xml object

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring

import threading

# ecc dependencies
import hashlib

import base64
from textwrap import wrap

import logging 	#not really needed but silences ajax logs (occurring once per second per client) 
				#see variable suppress_werkzeugs_logs 

from socket import error as socket_error

import struct



app = Flask(__name__)

html_template_file = 'interface.html'
html_template_update = 'update.html'

target_ip = '127.0.0.1'
#target_ip = '192.168.178.80'
#target_ip = 'localhost'
#target_ip = '141.89.175.111'
target_port = 44555
target_username = 'user'
target_password = 'admin'

app.config['MQTT_BROKER_URL'] = target_ip
app.config['MQTT_BROKER_PORT'] = 1883
# for auth, config is ['MQTT_USERNAME'] and ['MQTT_PASSWORD']
app.config['MQTT_REFRESH_TIME'] = 1.0

device_dict={}
nonce_dict={}
sensor_dict={}

script_root=''

script_error=""
script_notification=""
script_notification_old="will get overwritten after first notification"
script_notification_counter=0

global_rpc_lock = threading.Lock()

# For benchmarking
benchmark_array_part =[]
benchmark_array_whole =[]
start_update = 0
end_update = 0

# For update slicing
UPDATE_SLICE_SIZE = 600 # Bytes

# Update slice transmission flow control
UPDATE_FLOW_CONTROL_TYPE = 0 # Options: 0 = Using MQTT ACKs, 1 = Using sleep calls
UPDATE_SLICE_ACK = "OK" # Expected ACK content (used only if UPDATE_FLOW_CONTROL_TYPE == 0)
UPDATE_SLICE_RESPONSE_TOPIC_SUFFIX = "/response" # Suffix to append to update slice topic from ontology (used only if UPDATE_FLOW_CONTROL_TYPE == 0)
UPDATE_SLICE_SLEEP_TIME = 0.585 # seconds (used only if UPDATE_FLOW_CONTROL_TYPE == 1)

unacked_slices = {}

#silencing werkzeug logs
suppress_werkzeugs_logs = True

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


@app.route("/update/<thing>/", methods=['POST', 'GET'])
def update(thing):
	global script_root  # needed for ajax.js
	script_root = url_for('root', _external=True)
	clear_data()

	if ('m' in globals() and m.connected):  # checks for existing manager (NETCONF connection) to get devices
		get_update_device_dict(device=thing)
	else:  # (re)connects if not connected to NETCONF Server
		async_establish_manager_connection()

	return render_template(html_template_update, things_list=list_things(), errors=script_error)

#ajax used for errors, notifications, and providing sensor data
@app.route('/ajax', methods= ['GET'])
def ajax():
	global script_notification
	global script_update_nonce
	global script_notification_old
	global script_notification_counter

	#used for making notification disappear after a while
	if(script_notification_old==script_notification):
		script_notification_counter+=1
	if(script_notification_counter>8):
		script_notification=""
		script_notification_counter=0

	script_notification_old=script_notification

	json = jsonify(error=script_error, notification=script_notification, sensors=sensor_dict, nonce=nonce_dict)

	return json

toSend = []

"""
	function that handles multipart forms like publishing the update manifest or update image 
"""
@app.route('/function_call/<thing>/<function>/',methods=['POST'])
def multipart_function_click(thing, function):
	global toSend
	global start_update
	global benchmark_array_part
	global unacked_slices
	global device_dict
	clear_ajax()
	toSend = []

	if ('m' in globals() and m.connected):  # checks for existing manager (NETCONF connection) to get
		get_device_dict()
	else:  # (re)connects if not connected to NETCONF Server
		async_establish_manager_connection()

	if(function == "funcPubUpdateImage"):
		i = 0
		slice_topic = device_dict[thing][1]['rpcs']['updateDevice'][4] + '/' + thing
		response_topic = slice_topic + UPDATE_SLICE_RESPONSE_TOPIC_SUFFIX
		benchmark_array_part.clear()
		unacked_slices[response_topic] = []

		start_update = time.time()

		if UPDATE_FLOW_CONTROL_TYPE == 0:
			mqtt.subscribe(response_topic)

		while True:
			start_part = time.time()
			slice = request.files["inputUpdateImage"].read(UPDATE_SLICE_SIZE)
			if not slice:
				break
			msg = struct.pack(str(len(str(i))) + 'sc' + str(len(slice)) + 's', bytes(str(i), 'utf-8'), bytes(',', 'utf-8'), slice)
			mqtt.publish(slice_topic, msg)

			if UPDATE_FLOW_CONTROL_TYPE == 0:
				# Wait for response
				unacked_slices[response_topic].append(i)
				milliseconds_waited = 0
				while milliseconds_waited < 120000: # = 2 minutes
					if i in unacked_slices[response_topic]:
						time.sleep(0.1)
						milliseconds_waited += 100
						# Time out after 1 minute if no ACK received
						if milliseconds_waited == 60000:
							break
						# Re-send slice every 5 seconds if no ACK received
						if milliseconds_waited % 5000 == 0:
							mqtt.publish(slice_topic, msg)
					else:
						break
				if i not in unacked_slices[response_topic]:
					i += 1
			elif UPDATE_FLOW_CONTROL_TYPE == 1:
				time.sleep(UPDATE_SLICE_SLEEP_TIME)
				i += 1

			end_part = time.time()
			benchmark_array_part.append(end_part - start_part)

		if UPDATE_FLOW_CONTROL_TYPE == 0:
			mqtt.unsubscribe(response_topic)

		if len(unacked_slices[response_topic]) == 0 or UPDATE_FLOW_CONTROL_TYPE == 1:
			# Send final RPC
			n = xml_.to_ele('<' + function + '/>')  # NETCONF expects data in form of XML
			child = etree.SubElement(n, "uuidInput")
			child.text = thing
			inputParameters = etree.SubElement(n, "inputUpdateImage")
			inputParameters.text = "FIN"
			toSend.append(copy.deepcopy(n))
		else:
			print("Update transmission aborted due to timeout of slice " + str(i) + ".")
	else:
		# build the xml rpc call with post data
		signingString = ""
		#iterate through keys and add them sorted
		i = 0
		for key, value in sorted(request.form.items()):
			n = xml_.to_ele('<' + function + '/>')  # NETCONF expects data in form of XML
			child = etree.SubElement(n, "uuidInput")
			child.text = thing
			signingString = signingString + value + ";"
			# because the data is already base16 encoded
			inputParameters = etree.SubElement(n, key)
			# Convert to base16 for better handling of binary data
			inputParameters.text = str(i) + "," +value
			toSend.append( copy.deepcopy(n))
			i += 1
		# search and add outer signature
		signingString = signingString.rstrip(';')
		if("input_9_OuterSignature" in request.form.keys()):
			pass
		# generate signature
		elif(function == "funcPubUpdateManifest"):
			n = xml_.to_ele('<' + function + '/>')  # NETCONF expects data in form of XML
			child = etree.SubElement(n, "uuidInput")
			child.text = thing
			hashString = hashlib.sha256(signingString.encode()).hexdigest()
			#print("hashString is: ", hashString)
			#print("[+] signing String: ", signingString)
			out = subprocess.Popen(['./createSig', 'signU', signingString], stdout=subprocess.PIPE)
			#out = subprocess.Popen(['./createSig' , 'signU ' , ' "' ,signingString,'"'], stdout=subprocess.PIPE,
			#					   stderr=subprocess.STDOUT)
			stdout, stderr = out.communicate()
			outerSignature = str(stdout.decode("utf-8")).strip("\n")
			print(outerSignature)
			#outerSignature = sk.sign_deterministic( signingString.encode(), sigencode=sigencode_der)
			inputParameters = etree.SubElement(n, "input_9_OuterSignature")
			inputParameters.text = str(i) + "," + outerSignature
			toSend.append(copy.deepcopy(n))
			i += 1
			n = xml_.to_ele('<' + function + '/>')  # NETCONF expects data in form of XML
			child = etree.SubElement(n, "uuidInput")
			child.text = thing
			inputParameters = etree.SubElement(n, "input_9_OuterSignature")
			inputParameters.text = str(i) + "," + "START-UPDATE"
			toSend.append(copy.deepcopy(n))
			pass

	# Send RPCs
	t = Thread(target=rpc_call_seq)  # async because it can take a while
	t.start()  # and we don't want to block the main thread

	return render_template(html_template_file, things_list=list_things(),
						   selected_rpc_text=Markup(constants.make_rpc_info(thing, function, "")),
						   errors=script_error)

import time
#user clicked an rpc button
@app.route('/function_call/<thing>/<function>',defaults={'param_type' : None,'param_name': None, 'value': None},methods=['GET', 'POST'])
@app.route('/function_call/<thing>/<function>/<param_type>/<param_name>/<value>',methods=['GET', 'POST'])
@app.route('/function_call/<thing>/<function>/',methods=['POST'])
#@app.route('/function_call/<thing>/<function>/<param_type>/<param_name>/>',defaults={'value': None},methods=['GET','POST'])
def function_click(thing, function, param_type, param_name, value):
	clear_ajax()

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
	if(value!=None):							#if parameter value, add xml-node
		child = etree.SubElement(n, param_name)
		child.text = value
	else:							
		value = ""
				
	print("Request:")
	print(xml_.to_xml(n,pretty_print=True))
	
	t = Thread(target=rpc_call, args=(n,)) 	#async because it can take a while
	t.start()								#and we don't want to block the main thread

	return render_template(html_template_file, things_list=list_things(),
	selected_rpc_text= Markup(constants.make_rpc_info(thing,function,value)), errors=script_error)

#generating and sending the actual call
def rpc_call_seq():
	global script_notification
	global benchmark_array_part
	global benchmark_array_whole
	global start_update
	global end_update

	current_count = 1
	try:
		count__to_send = len(toSend)
		start = time.time()
		for newn in toSend:
			start_part = time.time()
			#print(xml_.to_xml(newn, pretty_print=True))
			rpc_reply = m.dispatch(newn) 							#dispatches the request
			#print(str(rpc_reply))
				#gets reply to put it in notification
			end_part = time.time()
			print("TEILNACHRICHT", current_count, "von", count__to_send , ": ", str(end_part - start_part))
			benchmark_array_part.append(end_part - start_part)
			print("SUMME bis JETZT: ", str(end_part - start))
			if newn == toSend[-1]:
				rpc_reply_xml_root = ET.fromstring(str(rpc_reply))
			else:
				current_count += 1
				# wait for MYNO-Device
				# time.sleep(0.2)
				continue
			for data_node in rpc_reply_xml_root.findall('./data'):
				for retval_node in data_node.findall('./retval'):
					try:
						returnValues = retval_node.text.split(',')
						# handle return values for the update function + ajax routing
						# route the values to ajax scriptS
						if newn.tag == "funcGetDeviceToken":
							nonce_dict["input_8_DeviceNonce"] = returnValues[0]
							nonce_dict["input_6_OldVersion"] = returnValues[1]
						# Set as Notification Text
						script_notification = constants.rpc_notification_text(retval_node.text)
					except Exception as e:
						print(str(e))

		end = time.time()
		print("TOTAL (Teilnachrichten): ", str(end - start))

		if start_update > 0:
			end_update = time.time()
			print("TOTAL (Update-Upload): ", str(end_update - start_update))
			benchmark_array_whole.clear()
			benchmark_array_whole.append(end_update - start_update)
			start_update = 0
			f = open('benchmark_update_parts.csv', 'w')
			with f:
				writer = csv.writer(f)
				writer.writerow(benchmark_array_part)
			f = open('benchmark_whole_update.csv', 'w')
			with f:
				writer = csv.writer(f)
				writer.writerow(benchmark_array_whole)

	except Exception as e:
		set_script_error("request error, connection still active? Netconf still running? Log: "+str(e))
		print(script_error)


#generating and sending the actual call
def rpc_call(n):
	global script_notification
	try:
		rpc_reply = m.dispatch(n) 							#dispatches the request
		print(str(rpc_reply))
		rpc_reply_xml_root = ET.fromstring(str(rpc_reply))	#gets reply to put it in notification
		for data_node in rpc_reply_xml_root.findall('./data'):
			for retval_node in data_node.findall('./retval'):
				returnValues = retval_node.text.split(',')
				# handle return values for the update function + ajax routing
				if n.tag == "funcGetDeviceToken":
					print(returnValues)
					nonce_dict["input_8_DeviceNonce"] = returnValues[0]
					nonce_dict["input_6_OldVersion"] = returnValues[1]
				script_notification = constants.rpc_notification_text(retval_node.text)
	except Exception as e:
		set_script_error("request error, connection still active? Netconf still running? Log: "+str(e))
		print(script_error)


def get_update_device_dict(*args, **kwargs):
	global m
	global device_dict

	device_name = kwargs.get('device', None)

	try:
		device_dict = get_update_devices(m)  # imported from getcaller.py
		if(device_name != None):
			for dict_value in list(device_dict):
				print(dict_value)
				if(dict_value != device_name):
					del device_dict[dict_value]
				#filter_dict = device_dict[device_name]
				#device_dict = filter_dict

		print("TEST")
		print(device_dict)
	except (NameError, Exception) as ee:
		if (ee.__class__.__name__ == "NameError"):
			set_script_error('exception in get_devices(). '
							 + 'Probably manager not connected. ' + 'Log: ' + str(ee))
		else:
			set_script_error('exception in get_devices(). Log: ' + str(ee)) + ee
		print(script_error)


def get_device_dict():
	global m
	global device_dict
	
	try:	
		device_dict = get_devices(m) #imported from getcaller.py
		print("TEST")
		print(device_dict)
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
		for device_uuid, dict_value in device_dict.items():
			
			#thing's name and ID as header for each thing "section"
			content = content + constants.make_thing_text(dict_value[0]);
			content = content + constants.make_thing_id_text(device_uuid);
			
			#RPCs, are going to be buttons
			functions = dict_value[1]['rpcs']

			functions_content = ""

			if (functions):								#key: 	rpc name (displayed+called)
				fitems = functions.items()
				for key, value in sorted(fitems): 	#value: array of:
															#0 description (displayed on hover)
															#1 possible parameter leaf name
															#2 possible parameters to pass
					
					if(value[2] == 'union'):
						functions_content = functions_content + constants.make_parameter_form(device_uuid, key, value[0],value[1],value[2], value[3])
					# create form when there is multiple inputs
					elif(type(value[1]) == list and len(value[1]) >= 1):
						functions_content = functions_content + constants.make_multipart_parameter_form(device_uuid, key, value[0], value[1], value[2])
					elif(value[2]): #enumeration or empty #if RPC parameters contains parameters to pass
						functions_content = functions_content + constants.make_parameter_button(device_uuid, key, value[0], value[1], value[2], value[3])
					elif(key == "updateDevice"):
						functions_content =  constants.make_update_button(device_uuid, key, value[0])+ functions_content
					else:
						functions_content = functions_content + constants.make_function_button(device_uuid, key, value[0])
			content = content + functions_content
			#sensor data, going to be text fields updated by ajax.js
			sensors = dict_value[1]['sensors']
			if (sensors):	
				content = content + constants.make_linebreak()
				for key, value in sensors.items():
					content = content + constants.make_sensor_tf(key, value)
					if(mqtt):
						mqtt.subscribe(value)
					else:
						setup_mqtt()
						mqtt.subscribe(value)
		
	else:
		content = constants.make_linebreak() \
		+ constants.make_thing_id_text("No devices available, press \"Get Devices\" to refresh.")
			
	return Markup(content);1


def async_establish_manager_connection():
	threading.Thread(target=establish_manager_connection).start()

#connects to NETCONF server via manager
def establish_manager_connection():
	global m
	try:
		m = manager.connect_ssh(target_ip, port=target_port, username=target_username,
		password=target_password,allow_agent=False,hostkey_verify=False,look_for_keys=False, manager_params={"timeout": 300})
		
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
		global unacked_slices
		print("Received message '" + str(message.payload.decode()) + "' on topic '" + message.topic + "'.")

		if message.topic in unacked_slices:
			payload = str(message.payload.decode()).split(',')
			if int(payload[0]) not in unacked_slices[message.topic]:
				print("Received response for unknown slice " + payload[0] + ".")
				return
			if payload[1] == UPDATE_SLICE_ACK:
				unacked_slices[message.topic].remove(int(payload[0]))
				print("Received ACK for slice " + payload[0] + ".")
		else:
			sensor_dict[message.topic]=(message.payload.decode(), constants.get_timestamp())
			#sensor_dict[message.topic]=(message.payload.decode(), constants.get_timestamp())
			#sensor_dict contains sensor values for each subscribed topic, gets queried at '/ajax' route


def set_script_error(error_string):
	global script_error
	script_error = error_string

		
def clear_data():
	clear_device_dict()
	clear_ajax()
	
def clear_device_dict():
	global device_dict
	try:
		device_dict.clear()
		sensor_dict.clear()
	except Exception as e:
		print(e)
	
def clear_ajax():
	global script_error 
	global script_notification 
	global script_notification_counter

	script_error=''
	script_notification=''
	script_notification_counter=0

if __name__ == "__main__":
	threading.Thread(target=setup_mqtt).start()	#MQTT client for sensor values
	async_establish_manager_connection()		#manager connection for scheme and RPCs
	app.run(debug=True, host='0.0.0.0')			#flask webserver launch
