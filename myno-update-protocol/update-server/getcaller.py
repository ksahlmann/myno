from interpret_get import get
from interpret_get_scheme import get_scheme


def get_update_devices(m):
	device_dict = get_devices(m, update=1)

	for thing in list(device_dict):
		temp_dict = device_dict[thing]
		for another_thing in list(temp_dict):
			if isinstance(another_thing, dict):
				for item in list(another_thing):
					if item != "rpcs":
						another_thing[item] = 0
						print("[+] DEBUG, deleting: ", item)
					else:
						for call in list(another_thing[item]):
							if(call != "funcPubUpdateImage" and call != "funcGetDeviceToken" and call != "funcPubUpdateManifest"):
								print(another_thing[item][call])
								del another_thing[item][call]

	#list(d):
	return device_dict

def get_devices(m, *args, **kwargs):

	parseUpdate = kwargs.get('update', None)

	device_dict={}

	devices=get(m) 				#dict of devices {UUID : (category , namespace)}

	scheme_dict=get_scheme(m, update=parseUpdate)	#dict of rpc/sensor info (namespace :
								#	{'rpcs':{name: {descr, param_name, parameters}}, 
								#	{'sensors': {name: topic}}
								#)
	print(scheme_dict)
	
	for key, value in devices.items():
		device_dict[key]=(value[0], scheme_dict[value[1]])
							#   0 is type(led-lamp),  1 contains uri to identify

	print("\ngetcaller device dict:")
	print(device_dict)			#dict of devices + rpc/sensor info {UUID: (category, scheme_dict)}
	return device_dict 
	

if __name__ == "__main__": #won't be called by webserver but useful for testing this class standalone
	from ncclient import manager
	m = manager.connect_ssh("192.168.178.80", port=44555, username="al", password="admin", allow_agent=False,
							hostkey_verify=False, look_for_keys=False)
	print("getcaller called by main")
	get_devices(m)