import xml.etree.ElementTree as ET
import json
import pyang

import namespaceparser

from yang2yin_direct import direct_yang2yin_call
from ncclient import manager


import xml.dom.minidom #as xmlprinter

modules={}

def get_scheme(m, *args, **kwargs):
	parseUpdate = kwargs.get('update', None)

	get_schema_string=(str(m.get_schema('')))

	print("  ")
	print(" > get_schema()")
	print(get_schema_string)

	root = ET.fromstring(get_schema_string)
	
	scheme_message_id=root.attrib.get("message-id")

	for child in root:
		if("data" in child.tag):
			scheme_data=child.text

	print ("scheme_message_id *",scheme_message_id)

	if(scheme_data):
		print ("scheme_data")
	else:
		print ("scheme_data not existing, breaking interpret_get_scheme")
		return

	multimodule = scheme_data.split("module")
	if len(multimodule) > 2:
		print("Multiple Modules found, splitting")
		xml_root = []
		for s in multimodule[1:]:
			xml_scheme = direct_yang2yin_call("module" + s)
			xml_root.append(ET.fromstring(xml_scheme) )
	else:
		xml_scheme = direct_yang2yin_call(scheme_data)
		xml_root = [ ET.fromstring(xml_scheme) ]

	print(xml_scheme)

	

	print ("parsing yin complete")
	
	for root in xml_root:
		for module in root.findall('.'):
			rpcs={}
			sensors={}
			rpc_names=[]
			rpc_descriptions=[]
			
			#rpc calls
			# udpate_functions counts if there are all needed methods for a update
			update_functions = 0
			calls = namespaceparser.findall(module,'./','rpc')
			for rpc in calls:
				if (parseUpdate == 1 or rpc.attrib['name'] != "funcPubUpdateManifest" and rpc.attrib['name'] != "funcGetDeviceToken" and rpc.attrib['name'] != "funcPubUpdateImage"):
					rpc_name=rpc.attrib['name']
					rpc_description=namespaceparser.find(namespaceparser.find(rpc,'./','description'),'./','text').text

					#the following block is used for getting parameter information
					param_name=[]
					param_type_name =[]
					parameters=[]
					leaf_list = namespaceparser.find(rpc, './', 'input')
					#inputs_list = namespaceparser.find(rpc, 'input')
					for leaf in leaf_list:
						if(leaf.attrib['name'] != "uuidInput"): #uuidInput is standard, we are interested in other ones
							list_param_type = namespaceparser.findall(leaf, './', 'type')
							for param_type in list_param_type:
								param_type_name.append(param_type.attrib['name'])
							param_name.append(leaf.attrib['name'])
							for parameter in namespaceparser.find(leaf,'./','type'):
								parameters.append(parameter.attrib['name'])
								print(parameter.attrib['name'])

					rpcs[rpc_name]=(rpc_description, param_name, param_type_name, parameters)
					print(rpcs[rpc_name])
				else:
					if rpc.attrib['name'] == "funcPubUpdateImage":
						slice_topic = namespaceparser.find(rpc,'./','default').attrib['value']
					update_functions +=1
					if update_functions == 3:
						rpc_name = "updateDevice"
						rpc_description = "Update the Device"
						param_name = []
						param_type_name = []
						parameters = []
						rpcs[rpc_name] = (rpc_description, param_name, param_type_name, parameters, slice_topic)

			
			#sensor data
			for container in namespaceparser.findall(module,'./','container'):
				for telemetry in namespaceparser.findall(container,'./','container'):
					for leaf in namespaceparser.findall(telemetry,'./','leaf'):
						leaf_name = leaf.attrib['name'] #LEAF NAME
						
						leaf_description = (namespaceparser.find(namespaceparser.find(leaf,'./','description'),'./','text')).text #description
						datapoint = (namespaceparser.find(leaf,'./','container'))
						
						for leaf in namespaceparser.findall(datapoint,'./','leaf'):
							leaf_name0 = leaf.attrib['name'] #LEAF NAME
							
							default = namespaceparser.find(leaf,'./','default')
							sensors[leaf_name]=default.attrib['value']
			
			for namespace in namespaceparser.findall(module,'./','namespace'):
				namespace_uri=namespace.attrib['uri']
				components={}
				components["rpcs"] = rpcs
				
				components["sensors"] = sensors
				modules[namespace_uri]=components

	return modules

def get_scheme_debug(m):
	main(m)
	print(modules)
	return modules
	

if __name__ == "__main__": #won't be called by webserver but useful for testing this class standalone
	m = manager.connect_ssh("localhost", port=44555, username="user", password="admin", allow_agent=False,
							hostkey_verify=False, look_for_keys=False)
	print("interpret_get_scheme called by main")
	get_scheme_debug(m)
   
