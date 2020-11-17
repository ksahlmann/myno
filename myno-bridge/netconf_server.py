# -*- coding: utf-8 -*-#
#
# February 23 2017, Thomas Scheffler <scheffler@beuth-hochschule.de>
# August 2017, Alexander H. W. Lindemann <allindem@cs.uni-potsdam.de>
# August 2018-2020, Kristina Sahlmann <sahlmann@uni-potsdam.de>
#
# Copyright (c) 2017
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from __future__ import absolute_import, division, unicode_literals, print_function, nested_scopes
import getpass
import logging
from lxml import etree
from netconf import server as netconf_server
from ncclient.xml_ import new_ele, sub_ele, to_xml
import paho.mqtt.client as mqtt

from kafka.json_generator import generate_json_kafka
from yang_generator_rdflib import generate_yang, delete_yang_module
import threading
import traceback

import time

CREATE_TOPIC = 'yang/config/create'
CREATE_RESPONSE_TOPIC = 'yang/config/create/response/'
RETRIEVE_TOPIC = 'yang/config/retrieve'
RETRIEVE_RESPONSE_TOPIC = 'yang/config/retrieve/response/'
UPDATE_TOPIC = 'yang/config/update'
UPDATE_RESPONSE_TOPIC = 'yang/config/update/response/'
DELETE_TOPIC = 'yang/config/delete'
DELETE_RESPONSE_TOPIC = 'yang/config/delete/response/'

NC_PORT = 44555 #default (by RFC 6242) 830, but using unprivileged port for testing
NC_DEBUG = True

BROKER_ADDR = "127.0.0.1"
BROKER_PORT = 1883
NAMESPACE = "https://www.cs.uni-potsdam.de/bs/research/myno/"

logger = logging.getLogger("onem2m-netconf-server")
nc_server = None #global server handle
yangModel = ""
command_dict = {}
uuid_set = set()
device_category = {}
device_list = {}
ctrl_func_list = {}
op_list = {}

global_responses = {}
global_request_id = 0
global_id_lock = threading.Lock()

global_config_dict = {}
global_config_dict_lock = threading.Lock()

class NetconfMethods (netconf_server.NetconfMethods):

    #build the config 
    #TODO What does this mean, where is it used ? 
    #THIS IS IMPORTANT, FURTHER CHECKS ARE NEEDED
    nc_config = new_ele('config')
    configuration = sub_ele(nc_config, 'configuration')
    system = sub_ele(configuration, 'system')
    location = sub_ele(system, 'location') 
    sub_ele(location, 'building').text = "Main Campus, A"
    sub_ele(location, 'floor').text = "5"
    sub_ele(location, 'rack').text = "27"
    
    #return device list with uuid and category
    @classmethod    
    def rpc_get (cls, unused_session, rpc, *unused_params):
        root = etree.Element('data')
        
        
        for ele in uuid_set:    
            child1 = etree.SubElement(root, 'device', xmlns=NAMESPACE+device_category[ele]) #TODO MAKE VARIABLE
            #child1 = etree.SubElement(root, 'device', xmlns="http://ipv6lab.beuth-hochschule.de/led") #TODO MAKE VARIABLE
            child2 = etree.SubElement(child1, "device-id")
            child3 = etree.SubElement(child2, "uuid")
            child3.text = ele
            child4 = etree.SubElement(child1, "device-category")
            child4.text = device_category[ele]
            #child4.text = "led"

        return root

    #return schema (yang model)
    def rpc_get_schema(self, unused_session, rpc, *unused_params):
        root = etree.Element("data", xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring")
        root.text = etree.CDATA(yangModel)
        return root
       
    #test method        
    def rpc_hubble (self, unused_session, rpc, *unused_params):
        return etree.Element("okidoki")    


def setup_module (unused_module):
    global nc_server

    if nc_server is not None:
        logger.error("XXX Called setup_module multiple times")
    else:
        sctrl = netconf_server.SSHUserPassController(username="user",
                                             password="admin")
        try:
            nc_server = netconf_server.NetconfSSHServer(server_ctl=sctrl,
                                            server_methods=NetconfMethods(),
                                            port=NC_PORT,
                                            host_key="host.key",
                                            debug=NC_DEBUG)
        except Exception as error:
            print(error)



### Generate Netconf Methods
def build_Netconf_Methods(method_Name):
    logger.info("build_Netconf_Method start generation of: " + method_Name)
    ld = {}
    
    exec("""
def rpc_%s(self, unused_session, rpc, *unused_params):
    return rpc_2_mqtt_bridge_fctn("%s", unused_params)
    """ % (method_Name, method_Name), None, ld)
   
    for name, value in ld.items():
        setattr(NetconfMethods, name, value)
    
    #attach RPC to configuration
    rpc = sub_ele(NetconfMethods.configuration,"""rpc_%s""" % (method_Name))
    logger.info("build_Netconf_Method generated: " + method_Name)

def checkForParameter(name, params):
    for p in params:
        logger.info("checking " +name+" and " + p['id'])
        if name == (p['id'].split('#')[1]):
            return True
    return False

#function to generate mqtt-commands from rpc request
#method_Name -> netconf rpc method identifier
def rpc_2_mqtt_bridge_fctn(method_Name, *params):
    global global_request_id
    logger.info("rpc called: " + method_Name )
    if params == None:
        return

    # get unique id for request
    global_id_lock.acquire()
    req_id = global_request_id
    global_request_id = global_request_id + 1
    global_id_lock.release()

    uuid = ""
    sendParams = []
    for kk in params:
        for k in kk:
            print(to_xml(k,pretty_print=True))
            if k.tag == "uuidInput":
                uuid = k.text
            elif checkForParameter(k.tag, command_dict[method_Name][2]):
                sendParams.append(k)
                print("parameter k: " + str(k)) #debug ausgabe


    msg = str(req_id) + ";" + command_dict[method_Name][0]
    for p in sendParams:
        msg = msg + ";" + p.text
    topic = command_dict[method_Name][1] + "/" + uuid

    logger.info("Publishing " + msg + " to topic " + topic)
    mqtt_client.publish(topic, msg)
    time.sleep(0.2) #wait for ack

    response = None
    counter = 0

    # changed sleep timer to .2 seconds to respond faster
    while counter < 5*120:
        if  str(req_id) in global_responses:
            global_id_lock.acquire()
            response = global_responses[str(req_id)]
            global_id_lock.release()
            break
        time.sleep(0.2)  # Wait for ack
        counter = counter + 1 
    
    if response == None:
        response = "NO RESPONSE FROM DEVICE"

    root = etree.Element('data')
    retval = etree.SubElement(root, "retval")
    retval.text = response


    return root

    

###  MQTT functions
def mqtt_connect(mqtt_client, userdata, flags, rc):
    logger.info("Connected to broker with result code " + str(rc))
    mqtt_client.subscribe("yang/config/#")
    mqtt_client.subscribe("response/#")#TODO TEMPORARY

def mqtt_message(mqtt_client, userdata, msg):
    global yangModel, command_dict
    global uuid_set
    global device_category
    global device_list
    global ctrl_func_list
    global op_list

    logger.debug(msg.topic + " " + msg.payload.decode())
    a = (msg.topic.split("/"))
    # modularization for mqtt message processing
    if msg.topic == UPDATE_TOPIC:  # yang/config/update
        rawmsg = msg.payload.decode().split(";")
        upd_uuid = rawmsg[0]
        upd_conf = rawmsg[1]
        if upd_uuid in uuid_set:
            # TODO also for update constrained devices with END message, see create
            # UPDATE = DELETE + CREATE
            deleteDevice(upd_uuid)
            global_config_dict_lock.acquire()
            global_config_dict[upd_uuid] = upd_conf
            global_config_dict_lock.release()

        else:
            if upd_uuid in global_config_dict.keys() and upd_conf == "END":
                global_config_dict_lock.acquire()
                createDevice(upd_uuid)
                del global_config_dict[upd_uuid]
                global_config_dict_lock.release()
                logger.debug('update: send ok')
                mqtt_client.publish(UPDATE_RESPONSE_TOPIC + upd_uuid, 'OK')
            elif upd_conf == "END":
                logger.debug('update: send notfound')
                mqtt_client.publish(UPDATE_RESPONSE_TOPIC + upd_uuid, 'NOTFOUND')
    if msg.topic == DELETE_TOPIC:  # yang/config/delete
        del_uuid = msg.payload.decode()
        if del_uuid in uuid_set:
            deleteDevice(del_uuid)
            logger.debug('delete: send ok')
            mqtt_client.publish(DELETE_RESPONSE_TOPIC + del_uuid, 'OK')
        else:
            logger.debug('delete: send notfound')
            mqtt_client.publish(DELETE_RESPONSE_TOPIC + del_uuid, 'NOTFOUND')
    if msg.topic == RETRIEVE_TOPIC:
        read_uuid = msg.payload.decode()
        if read_uuid in uuid_set:
            logger.debug('retrieve: send ok')
            mqtt_client.publish(RETRIEVE_RESPONSE_TOPIC + read_uuid, 'OK')
        else:
            logger.debug('retrieve: send notfound')
            mqtt_client.publish(RETRIEVE_RESPONSE_TOPIC + read_uuid, 'NOTFOUND')
    if msg.topic == CREATE_TOPIC or msg.topic == 'yang/config':  # yang/config/create , compatible modus
        rawmsg = msg.payload.decode().split(";")
        uuid = rawmsg[0]
        conf = rawmsg[1]

        global_config_dict_lock.acquire()

        if conf == "END" and uuid not in uuid_set:
            createDevice(uuid)

            del global_config_dict[uuid]
            global_config_dict_lock.release()

            logger.debug('create: send ok')
            mqtt_client.publish(CREATE_RESPONSE_TOPIC + uuid, 'OK')
            return

        if uuid in global_config_dict:
            global_config_dict[uuid] = global_config_dict[uuid] + conf
        else:
            global_config_dict[uuid] = conf

        global_config_dict_lock.release()

        
    elif a[0] == "response":
        raw = msg.payload.decode().split(';')
        global_id_lock.acquire()
        global_responses[raw[0]] = raw[1]
        global_id_lock.release()

    printYangModel(yangModel)

def createDevice(uuid):
    global yangModel, uuid_set, command_dict, ctrl_func_list, device_category, device_list, op_list
    try:
        yangModel_l, command_dict_l, uuid_set_l, device_category_l, device_list_l, ctrl_func_list_l, op_list_l = generate_yang(global_config_dict[uuid])
        #kafka
        generate_json_kafka(global_config_dict[uuid])
    except Exception as err:
        #print(err)
        traceback.print_exc()
    yangModel = yangModel + yangModel_l  # append new yang model to stored one -> not a good idea for VD!
    printYangModel(yangModel)
    # add deviceList to global variable
    device_list[uuid] = device_list_l
    ctrl_func_list[uuid] = ctrl_func_list_l
    op_list[uuid] = op_list_l
    device_category[uuid] = device_category_l  # adding device category to device
    uuid_set |= uuid_set_l
    for i in command_dict_l:
        build_Netconf_Methods(i)
    command_dict = {**command_dict, **command_dict_l}  # merging new command dictionaries

    # debug ausgaben
    # print("command_dict" + str(command_dict))
    # print("uuid_set" + str(uuid_set))
    # print("device_category" + str(device_category))
    # print("device_list" + str(device_list)) #beim delete fuer neu generateYang
    # print("ctrl_func_list" + str(ctrl_func_list)) #beim delete fuer neu generateYang
    # print("op_list" + str(op_list)) #beim delete fuer neu generateYang

def deleteDevice(del_uuid):
    global yangModel, command_dict, ctrl_func_list, device_category, uuid_set, device_list, op_list

    uuid_set.remove(del_uuid)
    device_category.pop(del_uuid)
    # delete from YANGModel and re-generate it
    device_list.pop(del_uuid)
    ctrl_func_list.pop(del_uuid)
    op_list.pop(del_uuid)
    command_dict.clear()
    yangModel = ""
    for uuid, dev in device_list.items():
        yangModel_n, command_dict_n = delete_yang_module(dev, ctrl_func_list[uuid], op_list[uuid])
        yangModel = yangModel + yangModel_n

        for i in command_dict_n:
            build_Netconf_Methods(i)
        command_dict = {**command_dict, **command_dict_n}  # merging new command dictionaries

    # global_config_dict TODO?
    # delete generated rpc methods TODO?


def printYangModel(yangModel):
    print(yangModel)
    try:
        daten = open("yang/gen_yang.txt", "w")
        daten.write(yangModel)
        daten.close()
    except Exception as err:
        print('Behandle Laufzeitfehler: ', err)


### ENTRY POINT
if __name__ == "__main__":
    if NC_DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = mqtt_connect
    mqtt_client.on_message = mqtt_message

    ### Run....
    mqtt_client.connect(BROKER_ADDR, BROKER_PORT, 60)

    #mqtt_client.loop_forever()
    mqtt_client.loop_start()

    setup_module(None)

    logger.info("init complete, starting main loop")
    running = True
    while running:
        try:
            time.sleep(100000)
        except KeyboardInterrupt:
            logger.info("got keyboard interrupt")
            running = False
            
        
    logger.info("Shutting down!")
