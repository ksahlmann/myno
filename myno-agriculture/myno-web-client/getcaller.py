from interpret_get import get
from interpret_get_scheme import get_scheme


def get_devices(m):

	device_dict={}

	devices=get(m) 				#dict of devices {UUID : (category , namespace)}

	scheme_dict=get_scheme(m)	#dict of rpc/sensor info (namespace :
								#	{'rpcs':{name: {descr, param_name, parameters}}, 
								#	{'sensors': {name: topic}}
								#)

	print('SCHEME DICT: ' + str(scheme_dict))
	
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