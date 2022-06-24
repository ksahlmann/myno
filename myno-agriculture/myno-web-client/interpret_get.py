import xml.etree.ElementTree as ET
from ncclient import manager

devices={}

def get(m):
	devices.clear()

	get_string=str(m.get()) 

	print(get_string)
	tree = ET.fromstring(get_string)

	get_message_id=tree.attrib.get("message-id")

	for data in tree:
		if("data" in data.tag):
			scheme_data=data

	print ("get_message_id *",get_message_id)
	print ("scheme_data    *",scheme_data)	
	print (" - - - - - - - ",scheme_data)	

	for device in scheme_data:		
		if("device" in device.tag):
			device_namespace=(device.tag).partition('{')[-1].rpartition('}')[0]
			device_id_node=(device.find(device.tag+'-id'))
			print(device_id_node)
			
			if device_id_node is not None: 
				device_uuid=device_id_node.find('{'+device_namespace+'}uuid').text
				device_category=(device.find(device.tag+'-category')).text
				devices[device_uuid]=(device_category,device_namespace)
			else:
				print('device_id_node none, maybe no devices listed?')
				
	print(devices)
	return(devices)

	
if __name__ == "__main__": #won't be called by webserver but useful for testing this class standalone
	m = manager.connect_ssh("localhost", port=44555, username="user", password="admin", allow_agent=False,
							hostkey_verify=False, look_for_keys=False)
	print("interpret_get called by main")
	get(m)