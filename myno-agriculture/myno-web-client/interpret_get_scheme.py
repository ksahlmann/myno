import xml.etree.ElementTree as ET
import json
import pyang

import namespaceparser

from yang2yin_direct import direct_yang2yin_call
from ncclient import manager


import xml.dom.minidom #as xmlprinter

modules={}

def main(m):

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
			sensor_units={}
			rpc_names=[]
			rpc_descriptions=[]
			
			#rpc calls
			for rpc in namespaceparser.findall(module,'./','rpc'):
				#rpc_name=rpc.attrib['name'].replace("func","")
				rpc_name=rpc.attrib['name']
				rpc_description=namespaceparser.find(namespaceparser.find(rpc,'./','description'),'./','text').text
				
				#the following block is used for getting parameter information
				param_name=""
				param_type_name =""
				parameters=[]
				for leaf in namespaceparser.find(rpc,'./','input'):
					if(leaf.attrib['name'] != "uuidInput"): #uuidInput is standard, we are interested in other ones
						for param_type in namespaceparser.findall(leaf,'./','type'):
							param_type_name = param_type.attrib['name']
							param_name = leaf.attrib['name']

						if (len(namespaceparser.find(leaf,'./','type')) != 0): # nicht type 'None'
							if (namespaceparser.find(leaf,'./','type').attrib['name']== 'union'):
								# union is only RGB input for LED: has value ranges for each union member
								for parameter in  namespaceparser.find(leaf,'./','type'):
									value_range = namespaceparser.find(parameter,'./','range').attrib['value'].split("..")
									#parameters.append([parameter.attrib['name'].replace("input",""),value_range])
									parameters.append([parameter.attrib['name'],value_range])
							elif(namespaceparser.find(leaf,'./','type').attrib['name'] == 'enumeration'):
								#event/automation CRUD/Operator are enumerations of parameter values
								enums = []
								for enum in namespaceparser.findall(param_type,'./','enum'):
									print(enum)
									option = enum.attrib['name']
									enums.append(option)
								#parameters.append([leaf.attrib['name'].replace("input","").split("_")[2],enums])
								parameters.append([leaf.attrib['name'],enums])
							# ints like threshold might have value range associated
							elif(namespaceparser.find(leaf,'./','type').attrib['name'] == 'int'):
								for element in namespaceparser.findall(leaf, './', 'type'):
									value_range = namespaceparser.find(element, './', 'range').attrib['value'].split(
										"..")
									#parameters.append([leaf.attrib['name'].replace("input","").split("_")[2],namespaceparser.find(leaf,'./','type').attrib['name'], value_range])
									parameters.append([leaf.attrib['name'],namespaceparser.find(leaf,'./','type').attrib['name'], value_range])
						else: #type is none: z.B. event configuration: name,duration,interval
							if "_" in leaf.attrib['name'].replace("input",""):
								#parameters.append([leaf.attrib['name'].replace("input","").split("_")[2], namespaceparser.find(leaf,'./','type').attrib['name']])
								parameters.append([leaf.attrib['name'], namespaceparser.find(leaf,'./','type').attrib['name']])
							else:
								#parameters.append([leaf.attrib['name'].replace("input",""), namespaceparser.find(leaf,'./','type').attrib['name']])
								parameters.append([leaf.attrib['name'], namespaceparser.find(leaf,'./','type').attrib['name']])
				rpcs[rpc_name]=(rpc_description, param_name, param_type_name, parameters)
				print(rpcs[rpc_name])
			
			#sensor data
			for container in namespaceparser.findall(module,'./','container'):
				for telemetry in namespaceparser.findall(container,'./','container'):
					for leaf in namespaceparser.findall(telemetry,'./','leaf'):
						#leaf_name = leaf.attrib['name'].replace("func","") #LEAF NAME
						leaf_name = leaf.attrib['name']
						leaf_description = (namespaceparser.find(namespaceparser.find(leaf,'./','description'),'./','text')).text #description
						datapoint = (namespaceparser.find(leaf,'./','container'))
						
						for leaf in namespaceparser.findall(datapoint,'./','leaf'):
							leaf_name0 = leaf.attrib['name'] #LEAF NAME
							default = namespaceparser.find(leaf,'./','default')
							if namespaceparser.findall(leaf, './', 'units') == []:
								unit = ''
							else:
								unit = namespaceparser.findall(leaf, './', 'units')[0].attrib['name'].split(";")[1]
								if (unit == "%%"):
									unit = "%"
							sensors[leaf_name]=[default.attrib['value'],unit]
			for namespace in namespaceparser.findall(module,'./','namespace'):
				namespace_uri=namespace.attrib['uri']
				components={}
				components["rpcs"] = rpcs

				components["sensors"] = sensors
				modules[namespace_uri]=components

def get_scheme(m):
	main(m)
	print(modules)
	return modules


if __name__ == "__main__": #won't be called by webserver but useful for testing this class standalone
	m = manager.connect_ssh("localhost", port=44555, username="user", password="admin", allow_agent=False,
							hostkey_verify=False, look_for_keys=False)
	print("interpret_get_scheme called by main")
	get_scheme(m)
