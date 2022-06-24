var notificationDiv = document.getElementById('notification');
var rpcDiv = document.getElementById('selected_rpc');
var errorDiv = document.getElementById('error');
var eventDiv = document.getElementById('events');

document.addEventListener("DOMContentLoaded", function(event) { 
	getDivs();
	updateValues();
});

function getDivs() {
	notificationDiv = document.getElementById('notification');
	errorDiv = document.getElementById('error');
	eventDiv = document.getElementById('events');
	rpcDiv = document.getElementById('selected_rpc');
}

function updateValues() { //gets data from "/ajax"-path, then calls updateUI()
            
            var request = new XMLHttpRequest(); 
            
			request.onload = function(elements) { 
				var result = JSON.parse(request.responseText);
				console.log(result)
				updateUI(result)
				};
			
			request.open("GET", $SCRIPT_ROOT+"/ajax", true);
			request.send();

        }
setInterval(function() {
    updateValues();
}, 1000);

function updateUI(data) {

	if(!errorDiv || !notificationDiv || !eventDiv || !rpcDiv) {
		getDivs(); 	//needed because some browsers ignore the "DOMContentLoaded" listener 
	}				//or call it too early so we re-init the two variables

	//sensor values
	for (let key in data.sensors) {
    	let value = data.sensors[key];
    	var element = document.getElementById(key);
    	
    	if(element)
			element.innerText=(value[0]);
			if (key.includes("event")){
                if (value[0]!=""){
                    element.parentElement.className = 'sensor-event-triggered'
                }
                else{
                    element.parentElement.className = 'sensor-event-clear'
                }
        }
	}
		
	//notification and error popups
	if(data.error!=""){
		errorDiv.innerHTML=data.error;
		fadeIn(errorDiv, 1000);
	}
	else {
		fadeOut(errorDiv, 1000);
	}
	
	if(data.notification!=""){
		notificationDiv.innerHTML=data.notification;
		fadeIn(notificationDiv, 1000);
		}
	else {
		fadeOut(notificationDiv, 1000);
	}
	if(data.events!=""){
		eventDiv.innerHTML=data.events;
		fadeIn(eventDiv, 1000);
		}
	else {
		fadeOut(eventDiv, 1000);
	}
	if(data.selected_rpc!=""){
		rpcDiv.innerHTML=data.selected_rpc;
		fadeIn(rpcDiv, 1000);
		}
	else {
		fadeOut(rpcDiv, 1000);
	}
    if(document.getElementById('autom_rpc')){
        document.getElementById('autom_rpc').addEventListener('change', function () {
        var style = this.value.split(",")[1] == 'union' ? 'block' : 'none';
        for (i = 0; i < document.getElementsByClassName('hidden_rpc').length; i++) {
        document.getElementsByClassName('hidden_rpc')[i].style.display = style;
        }
        });
    }


}

//UI animations for notifications and errors

function fadeOut(element) {
	if(!element)
		return;
    	
    var opacity = parseFloat(window.getComputedStyle(element).getPropertyValue("opacity")); 
    var timer = setInterval(function () {
        if (opacity <= 0.001){
            clearInterval(timer);
            element.style.display = 'none';
        }
        element.style.opacity = opacity;
        element.style.filter = 'alpha(opacity=' + opacity * 100 + ")";
        opacity -= opacity * 0.1;
    }, 50);
}

function fadeIn(element, ms)
{
	if(!element)
		return;

	element.style.display = "inline-block";
	element.style.visibility = "visible";

	var opacity = parseFloat(window.getComputedStyle(element).getPropertyValue("opacity")); 

	if(ms) {
		var timer = setInterval(function() {
			opacity += 50 / ms;
			if(opacity >= 1) {
				clearInterval(timer);
				opacity = 1;
			}
			element.style.opacity = opacity;
			element.style.filter = "alpha(opacity=" + opacity * 100 + ")";
		}, 50);
	}
	else
	{
		element.style.opacity = 1;
		element.style.filter = "alpha(opacity=1)";
	}
}
