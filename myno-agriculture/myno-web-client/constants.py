import datetime

#HTML UI elements
def make_thing_text(text): #Thing Name
	content= """<br><p class="thing">"""+str(text)+"""</p>"""
	return content;

def make_thing_id_text(text): #gray UUID behind Thing Name
	content= """<p class="uuid">"""+str(text)+"</p></br>\n"
	return content;
	
def make_linebreak():
	content= "<br>\n"
	return content;
	
def make_function_button(thing, name, description):
	content= "<a href='/function_call/"+str(thing)+"/"+str(name)+"' class='button device_function_button' "+'title="'+str(description)+'"'+">"+str(name).replace("func","")+"</a>\n"
	return content;
	
def make_parameter_button(thing, name, description, param_name, param_type_name, parameters):
	parameter_entries = ""

	for parameter in parameters:
		parameter_entries = parameter_entries + "<p><a href='/function_call/" + str(thing) + "/" + str(name) + "/"  + str(param_type_name) + "/"  + str(param_name) + "/" + str(parameter) + "'>" + str(parameter) +  "</a></p>"

	content = " <div class='dropdown' 'title="+str(description)+"'> <span>" + name + " ▾</span> <div class='dropdown-content'>"
	return content + parameter_entries + "</div></div>"

def make_parameter_form(thing, name, description, param_name, param_type_name, parameters):
	parameter_entries = ""
	parameters.sort(reverse=True)
	for parameter in parameters:
		parameter_entries = parameter_entries + parameter[0] + ";"

	content = "<ul id='btnparameter' class = 'dropdown_parent'> <button class = 'device_parameter_button' title='" + str(
			description) + "'>" + str(name).replace("func","") + " ▾</button> <ul class='dropdown_child_parameter'><form class = 'form-inline' method = 'POST'> <div class ='dropdown-configuration'>"
#	content =" <form class = 'form-inline' action = '/function_call/" + str(thing) +  "/" + str(name) + "/" + str(param_type_name) + "/" + str(param_name) + "/" + str(parameter_entries) +"' method = 'POST'> <div class ='dropdown-input'>    <ul> <li class='detail' id='clickable'> <span data-tip='This is the text of the tooltip'>"+str(name) +" ▾ </span><ul>"

	for parameter in parameters:
		# List of parameters, where each has a min and max,
		# are simple input fields. So far these are only numerical parameters
		content = content + " <li> <p><label class=h2>" + parameter[
					0].replace("input","") + ":</label> <input type='number' id=" + str(parameter[0]) + " name =" + parameter[0] + " min='" + \
						  parameter[1][0] + "' max='" + parameter[1][1] + "' value = '" + parameter[1][
							  1] + "' required '>  </input></p></li>  "
	content = content + "<p><li><button type='submit' class='button device_submit_button' formaction = '/function_call/" + str(thing) +  "/" + str(name) + "/" + str(param_type_name) + "/" + str(param_name) + "/" + str(parameter_entries) +"'>submit</button></p>  </li > "
	content = content + "  </ul >  </li></ul > </div>"
	content = content + "</form>"
	return content;

def make_event_form(thing, name, description, param_name, param_type_name, parameters):
	parameter_entries = ""
	parameters.sort(reverse=False)
	for parameter in parameters:
		parameter_entries = parameter_entries + parameter[0] + ";"

	content = "<ul id='btnconfiguration' class = 'dropdown_parent'> <button class = 'device_configuration_button' title='" + str(
			description) + "'>" + str(name).replace("func","") + " ▾</button> <ul class='dropdown_child_config'><form class = 'form-inline' method = 'POST'> <div class ='dropdown-configuration'>"

	#content =" <form class = 'form-inline' action = '/function_call/" + str(thing) +  "/" + str(name) + "/" + str(param_type_name) + "/" + str(param_name) + "/" + str(parameter_entries) +"' method = 'POST'> <div class ='dropdown-configuration'>    <ul> <li class='detail'> <span>"+str(name) +" ▾ </span><ul>"
	for parameter in parameters:
	# Differentiate different parameter types
		# int with min max
		if parameter[1] == 'int' and len(parameter) > 2 and type(parameter[2])==list:
			content = content + "<li><p> <label class=h2>"+parameter[0].replace("input_","")+":</label> <input type='number' id="+str(parameter[0])+" name ="+parameter[0]+" min='" + parameter[2][0] + "' max='" + parameter[2][1] + "'step = 0.1 value = '1' required '>  </input></p></li>  "
		# int no min max (event interval and duration, set min/max 1/1000)
		elif parameter[1] == 'int':
			content = content + " <li><label class=h2>"+parameter[0].replace("input_","")+":</label> <input type='number' id="+str(parameter[0])+" name ="+parameter[0]+" min='1' max='1000' value = '1' required '>  </input></li>  "
		# floats, i.e. threshold
		elif parameter[1] == 'float':
			content = content + " <li><p> <label class=h2>"+parameter[0].replace("input_","")+":</label> <input type='number' id="+str(parameter[0])+" name ="+parameter[0]+" min='-100' max='100' value = '0' required step = 0.1 >  </input></p></li>  "
		# string, i.e. name, maxed at 15 characters
		elif parameter[1] == 'string':
			content = content + " <li><p> <label class=h2>"+parameter[0].replace("input_","")+":</label> <input type='text' id="+str(parameter[0])+" name ="+parameter[0]+"   maxlength='15' size='15'  required value='Default'  placeholder = 'Eventname'> </input></p></li>  "
		# list to select from, i.e. CRUD
		elif type(parameter[1]) == list:
			content = content + " <li> <label class=h2>"+parameter[0].replace("input_","")+":</label> <select onfocus='this.size=3;' onblur='this.size=1;' onchange='this.size=1; this.blur();' name="+parameter[0]+"> "
			for item in sorted(parameter[1]):
				content = content + "<option> "+str(item)+" </option >"
			content = content + "</select></li>"
	content = content + "<p><li><button type='submit' class='button device_submit_button' formaction = '/function_call/" + str(thing) +  "/" + str(name) + "/" + str(param_type_name) + "/" + str(param_name) + "/" + str(parameter_entries) +"'>submit</button></p>  </li > "
	content = content + "</ul ></li></ul ></div>"
	content = content + "</form>"
	return content;

def make_automation_form(thing,functions,name,description,param_name, param_type_name, parameters):#, name, description, param_name, param_type_name, parameters):
	rpcdict = {}
	evdict = {}
	parameter_entries = ""
	for parameter in parameters:
		parameter_entries = parameter_entries + parameter[0] + ";"
	# Collect all relevant functions: actuators and event configuration for this sensor
	for key, value in sorted(functions.items()):
		#skip automation function
		if('Auto' in key):
			continue
		elif('Conf' in key):
			# skip all event configurations except for this sensor
			if(key.replace("Conf","Auto",1) == name):
				evdict[key] = value
			else:
				continue
		else:
			rpcdict[key] = value
	content ="<ul id='btnconfiguration' class = 'dropdown_parent'> <button class = 'device_configuration_button' title='"+str(description)+"'>"+str(name).replace("func","")+" ▾</button> <ul class='dropdown_child_config' ><form class = 'form-inline' method = 'POST'> <div class ='dropdown-configuration'>"
	for key, value in sorted(evdict.items()):
		content = content + "<div id = " + str(key) + ">"
		# all parameters for an automation, name, operator, threshold ....
		for parameter in value[3]:
			if parameter[1] == 'int' and len(parameter) > 2 and type(parameter[2]) == list:
				content = content + "<li><p><label class=h2>" + parameter[0].replace("input_","") + ":</label> <input type='number' id=" + str(parameter[0]) + " name =" + parameter[0] +" min='" + parameter[2][0] + "' max='" + parameter[2][1] + "'step = 0.1 value = '1' required '>  </input></p></li>  "
			elif parameter[1] == 'int':
				content = content + " <li><label class=h2>" + parameter[0].replace("input_","") + ":</label> <input type='number' id=" + str(parameter[0]) + " name =" + parameter[0] + " min='1' max='1000' value = '1' required '>  </input></li>  "
			elif parameter[1] == 'float':
				content = content + " <li><p> <label class=h2>" + parameter[0].replace("input_","") + ":</label> <input type='number' id=" + str(parameter[0]) + " name =" + parameter[0] + " min='-100' max='100' value = '0' required step = 0.1 >  </input></p></li>  "
			elif parameter[1] == 'string':
				content = content + " <li><p> <label class=h2>" + parameter[0].replace("input_","") + ":</label> <input type='text' id=" + str(parameter[0]) + " name =" + parameter[0] + "   maxlength='16' size='16'  required value='Default'  placeholder = 'Eventname'> </input></p></li>  "
			elif type(parameter[1]) == list:
				content = content + " <li> <label class=h2>" + parameter[0].replace("input_","") + ":</label> <select name=" + parameter[0] + "> "
				for item in sorted(parameter[1]):
					content = content + "<option> " + str(item) + " </option >"
				content = content + "</select></li>"
		content = content + "</div>"
	# selection menu for all possible actuations
	content = content + "<div class=selector> <li> <select name='command' onfocus='this.size=3;' onblur='this.size=1;' onchange='this.size=1; this.blur();' id = autom_rpc required><option selected disabled>Actuator Command</option>"
	for key, value in sorted(rpcdict.items()):
		content = content + "<option value=" + str(key) +","+str(value[2])+ " > " + str(key) + " </option >"
	content = content + "</select></li></div>"
	# special case: RGB input, will reveal another layer to select three input values
	for key, value in sorted(rpcdict.items()):
		if (value[2] == 'union'):
			content = content + "<li><div class='hidden_rpc' style='display: none;'>"
			for i in range(len(value[3])):
				content = content + str(sorted(value[3],reverse=True)[i][0]) + ": <input type='number' name =" + sorted(value[3],reverse=True)[i][0] + " min='" + \
						  sorted(value[3],reverse=True)[i][1][0] + "' max='" + sorted(value[3],reverse=True)[i][1][1] + "' value = '" + sorted(value[3],reverse=True)[i][1][1] + "' required '>  </input>"
			content = content + "</div></li>"
	content = content + "<li><input type='submit' class='button device_submit_button'  value = 'submit' formaction='/function_call/"+str(thing)+"/"+ str(name) + "/" + str(param_type_name) + "/" + str(param_name) + "/" + str(parameter_entries)+"'></input> </li >  "
	content = content + "</ul></ul></div>"
	content = content + "</form>"
	return content;

def make_manifest_form(thing, name, description, param_name, param_type_name, parameters):
	parameter_entries = ""
	parameters.sort(reverse=False)
	for parameter in parameters:
		parameter_entries = parameter_entries + parameter[0] + ";"

	content = "<ul id='btnconfiguration' class = 'dropdown_parent'> <button class = 'device_configuration_button' title='" + str(
			description) + "'>" + str(name).replace("func","") + " ▾</button> <ul class='dropdown_child_config'><form class = 'form-inline' method = 'POST' enctype='multipart/form-data'> <div class ='dropdown-configuration'>"

	#content =" <form class = 'form-inline' action = '/function_call/" + str(thing) +  "/" + str(name) + "/" + str(param_type_name) + "/" + str(param_name) + "/" + str(parameter_entries) +"' method = 'POST'> <div class ='dropdown-configuration'>    <ul> <li class='detail'> <span>"+str(name) +" ▾ </span><ul>"
	for parameter in parameters:
	# Differentiate different parameter types
		# int with min max
		if parameter[1] == 'int' and len(parameter) > 2 and type(parameter[2])==list:
			content = content + "<li><p> <label class=h2>"+parameter[0].replace("input_","")+":</label> <input type='number' id="+str(parameter[0])+" name ="+parameter[0]+" min='" + parameter[2][0] + "' max='" + parameter[2][1] + "'step = 0.1 value = '1' required '>  </input></p></li>  "
		# int no min max (event interval and duration, set min/max 1/1000)
		elif parameter[1] == 'int':
			content = content + " <li><label class=h2>"+parameter[0].replace("input_","")+":</label> <input type='number' id="+str(parameter[0])+" name ="+parameter[0]+" min='1' max='1000' value = '1' required '>  </input></li>  "
		# string, i.e. name, maxed at 15 characters
		elif parameter[1] == 'string' or parameter[1] == 'hexBinary' and 'Image' not in name:
			content = content + " <li><p> <label class=h2>"+parameter[0].replace("input_","")+":</label> <input type='text' id="+str(parameter[0])+" name ="+parameter[0]+"   maxlength='1000' size='15'  required value='Default' > </input></p></li>  "
		elif parameter[1] == 'hexBinary' and 'Image' in name:
			content = content + " <li><p> <label class=h2>"+parameter[0].replace("input","")+":</label> <input type='file' id="+str(parameter[0])+" name ="+parameter[0]+"> </input></p></li>  "
	content = content + "<p><li><button type='submit' class='button device_submit_button' formaction = '/function_call/" + str(thing) +  "/" + str(name) + "/" + str(param_type_name) + "/" + str(param_name) + "/" + str(parameter_entries) +"'>submit</button></p>  </li > "
	content = content + "</ul ></li></ul ></div>"
	content = content + "</form>"
	return content;

def make_function_input(thing, name,description):
	content = "<a href='/function_call/"+str(thing)+"/"+str(name)+"</a>\n"
	return content;

def make_sensor_tf(name, thing):
	if (thing[0].split("/")[0] == 'event'):
		content = ''
	else:
		content= str(name)+": "
		content= "<div class='sensor'><p> "+str(name).replace("funcGet","")+"</p><span id='"+thing[0] + "' style=text-align:left>"+ " &nbsp&nbsp "+"</span>"+"&nbsp"+ thing[1] +"</div> \n"
	return content;

def make_sensor_event(name, thing):
	# new field for any sensor, which has event configuration. Changes state based on event
	content= str(name)+": "
	content= "<div class='sensor-event-clear'><p> "+str(name).replace("func","")+"</p><span id='"+thing[0] + "' style=text-align:left>"+ " &nbsp&nbsp "+"</span>"+"&nbsp"+ thing[1] +"</div> \n"
	return content;


def make_rpc_info(thing, rpc_text, value):
	if(value != ""): #generate string if parameter was passed
		value = "</b> set to <b> " + value
	content =	"selected rpc (" + get_timestamp() + "): "  + thing + " <b>" + rpc_text + value + "</b>"
	return content

#RPC return values
def rpc_notification_text(retvaltext):
	error_description = " ("+retvaltext+")"
	if(retvaltext == "OK"):
		error_description = "State has changed successfully" + error_description
	elif(retvaltext == "NOOP"):
		error_description = "No change, device has already been in this state" + error_description
	elif(retvaltext == "NACK"):
		error_description = "No change, rpc contained unknown control" + error_description
	else:
		error_description = error_description
	return get_timestamp()+" - "+error_description

#MISC method calls
def get_timestamp():
	return str(datetime.datetime.now().time().strftime('%H:%M:%S'))

def make_hline():
	return "<hr class=thingslist>"
