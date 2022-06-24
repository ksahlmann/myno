from ncclient import manager

m = manager.connect_ssh("127.0.0.1", port=44555, username="user", password="admin", allow_agent=False,hostkey_verify=False, look_for_keys=False)
# different methods: get (working), ping (not working). 
#result = str(m.get())
# also tried with different input m.ping('') or m.ping(); different errors -> see output
result = str(m.ping())
print(result)
