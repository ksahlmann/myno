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
	content= "<a href='/function_call/"+str(thing)+"/"+str(name)+"' class='button device_function_button' "+'title="'+str(description)+'"'+">"+str(name)+"</a>\n"
	return content;

def make_update_button(thing, name, description):
	content= "<a href='/update/"+ thing + "'"+'title="'+str(description)+'"'+">"+str(name)+"</a><br><br>"
	return content;
	
def make_parameter_button(thing, name, description, param_name, param_type_name, parameters):
	parameter_entries = ""

	for parameter in parameters:
		parameter_entries = parameter_entries + "<p><a href='/function_call/" + str(thing) + "/" + str(name) + "/"  + str(param_type_name) + "/"  + str(param_name) + "/" + str(parameter) + "'>" + str(parameter) +  "</a></p>"

	content = " <div class='dropdown' onclick=''> <span>" + name + " ▾</span> <div class='dropdown-content'>"
	return content + parameter_entries + "</div></div>"

# form for multiple parameters
def make_multipart_parameter_form(thing, name, description, param_name, param_type_name):
	parameter_entries = ""
	#str("/".join(param_name))
	content = "<div class='form_function' id='" + str(name) + "' ><form action = '/function_call/" + str(thing) +  "/" + str(name) + "/" + \
			  "' method = 'POST' enctype = 'multipart/form-data' >"
	content = content + "<div><fieldset><legend>" +str(name) +"<br> </legend ></div><table style='padding-bottom:10px!important'>"
	i = 0
	for parameter in param_name:
		type = "type='text'"
		if(param_type_name[i] == "int"):
			type = "type='number'"
			print("")
		elif(param_type_name[i] == "binary" and parameter == "inputUpdateImage"):
			type = "type='file'"
		if(parameter == "input_9_OuterSignature"):
			content = content + "<tr><td><label>" + parameter + ":</label></td> <td> <input " + type \
					  + "" + " id='" + str(parameter) + "'" + " name='" + parameter \
					  + "' class='form-control' disabled style='background-color: gray;'></div></td>"
		else:
			content = content + "<tr><td><label>" + parameter + ":</label></td> <td> <input " + type \
					  + "" + " id='" + str(parameter) + "'" + " name='" + parameter \
					  + "' class='form-control'></div></td> </tr>"
		i += 1
	content = content + "</table><button type='submit' class='button device_function_button'>"+description+"</button>"
	content = content + "</fieldset></form></div>"
	return content;

def make_parameter_form(thing, name, description, param_name, param_type_name, parameters):
	#content = "<form class = 'form-inline' form action = 'http://localhost:5000/login' method = 'POST'>"
	#content = ""
	parameter_entries = ""
	parameters.sort(reverse=True)
	for parameter in parameters:
		parameter_entries = parameter_entries + parameter + ";"
	content = "<div class='form_function'><form action = '/function_call/" + str(thing) +  "/" + str(name) + "/" + str(param_type_name) + "/" + str(param_name) + "/" + str(parameter_entries) +"' method = 'POST'>"
	content = content + "<fieldset><legend>" +str(name) +"<br> </legend >"
	for parameter in parameters:
		content = content + "<label>"+parameter+":</label>  <input type='number' id="+str(parameter)+" name =" + parameter + \
				  " min='0' max='255' value = 255 required maxlength='3' minlength = '1'     >"
	content = content + "<button type='submit' class='button device_function_button'>"+description+"</button>"
	content = content + "</fieldset></form></div>"
	return content;

def make_function_input(thing, name,description):
	content = "<a href='/function_call/"+str(thing)+"/"+str(name)+"</a>\n"
	return content;

def make_sensor_tf(name, thing):
	content= str(name)+": "	
	content= "<div class='sensor'> "+str(name)+"&nbsp <p id='"+thing+"'>"+" &nbsp&nbsp "+" </p></div> \n"
	return content;

def make_rpc_info(thing, rpc_text, value):
	if(value != ""): #generate string if parameter was passed
		value = "</b> set to <b> " + value
	content =	"selected rpc (" + get_timestamp() + ") <br> "  + thing + " <b>" + rpc_text + value + "</b>"
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
