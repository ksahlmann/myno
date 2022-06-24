#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <BH1750.h>
#include <string.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <esp_bt_main.h>
#include <esp_bt.h>
#include <esp_wifi.h>

// DEFINITIONS_
// Change often:
// Debug (if set to one, printing statements between ifdef endif will be done. comment out to disable)
//#define DEBUG 1
// SLEEP_CYCLE (if set to one, sleep is initiated at the end of loop. comment out to disable)
//#define SLEEP_CYCLE 1
// CRUD_SLEEP (if set to one, board will crud-delete before sleep and crud-update after wakeup. comment out to disable) 
//#define CRUD_SLEEP 1
 
// OVERALL
#define UUID "110A-4F4F-8F69-6B8F3C2E78ED"
#define BOARD "Board_10"

// SLEEP
#define uS_TO_S_FACTOR 1000000UL  /* Conversion factor for micro seconds to seconds */
#define TIME_TO_SLEEP  25UL      /* Time ESP32 will go to sleep (in seconds) */

// TIMING (used for waiting on response. After this time, board will try again or abort)
#define TIMEOUT 25000 //milliseconds

// ENDPOINTS for analog sensors: 4095 is default for dry environments. For calibration see documentation
#define MOISTURE_AIR 4095
#define MOISTURE_WATER 2018
#define RAIN_DRY 4095
#define RAIN_WET 1040

// Change less often:
// MQTT-TOPICS
// ACTUATOR TOPICS
#define LED1_TOPIC_S "actuator/led/led_1/"UUID
#define PUMP1_TOPIC_S "actuator/pump/pump_1/"UUID
// CRUD TOPICS
#define CONFIG_TOPIC_P "yang/config"
#define PING_TOPIC_S CONFIG_TOPIC_P"/ping"
#define CRUD_TOPICS_S CONFIG_TOPIC_P"/+/response/"UUID
#define CREATE_TOPIC_S CONFIG_TOPIC_P"/create/response/"UUID
#define RETRIEVE_TOPIC_S CONFIG_TOPIC_P"/retrieve/response/"UUID
#define UPDATE_TOPIC_S CONFIG_TOPIC_P"/update/response/"UUID
#define DELETE_TOPIC_S CONFIG_TOPIC_P"/delete/response/"UUID
#define PING_TOPIC_P CONFIG_TOPIC_P"/ping/response/"UUID
#define CREATE_TOPIC_P CONFIG_TOPIC_P"/create"
#define RETRIEVE_TOPIC_P CONFIG_TOPIC_P"/retrieve"
#define UPDATE_TOPIC_P CONFIG_TOPIC_P"/update"
#define DELETE_TOPIC_P CONFIG_TOPIC_P"/delete"

// SENSOR PUBLISHING TOPICS
#define RESPONSE_TOPIC_P "response/"UUID
#define BRIGHT1_TOPIC_P "sensor/brightness/brightness_1/"UUID
#define TEMP1_TOPIC_P "sensor/temperature/temperature_1/"UUID
#define HUM1_TOPIC_P "sensor/humidity/humidity_1/"UUID
#define PRES1_TOPIC_P "sensor/pressure/pressure_1/"UUID
#define RAIN1_TOPIC_P "sensor/rain/rain_1/"UUID
#define MOIST1_TOPIC_P "sensor/moisture/moisture_1/"UUID

// EVENT TOPICS (Notifications are sent to these)
#define BRIGHT1_TOPIC_EVENT "event/sensor/brightness/brightness_1/"UUID
#define TEMP1_TOPIC_EVENT "event/sensor/temperature/temperature_1/"UUID
#define HUM1_TOPIC_EVENT "event/sensor/humidity/humidity_1/"UUID
#define PRES1_TOPIC_EVENT "event/sensor/pressure/pressure_1/"UUID
#define RAIN1_TOPIC_EVENT "event/sensor/rain/rain_1/"UUID
#define MOIST1_TOPIC_EVENT "event/sensor/moisture/moisture_1/"UUID

// SENSOR CONFIG TOPICS -(Event/Automation CRUD operations)
#define BRIGHT1_CONFIG "config/sensor/brightness/brightness_1/"UUID
#define TEMP1_CONFIG "config/sensor/temperature/temperature_1/"UUID
#define HUM1_CONFIG "config/sensor/humidity/humidity_1/"UUID
#define PRES1_CONFIG "config/sensor/pressure/pressure_1/"UUID
#define RAIN1_CONFIG "config/sensor/rain/rain_1/"UUID
#define MOIST1_CONFIG "config/sensor/moisture/moisture_1/"UUID
#define SENSOR_CONFIG_S "config/sensor/+/+/"UUID

// SENSOR AUTOMATION TOPICS
#define MOIST1_AUTOM "automation/sensor/moisture/moisture_1/"UUID
#define SENSOR_AUTOM_S "automation/sensor/+/+/"UUID

// CRUD RESPONSES
#define CRUD_OK "OK"
#define CRUD_NOTOK "NOTFOUND" // not used

//General ERROR TOPIC
#define ERROR_P "error"
 
// Alarm/Event Struct
#define NUMBER_OF_EVENTS 5
typedef struct 
{ 
  char ename[16] =""; 
  char eoperator[3]=""; /* one of: <, <=, ==, >=, > */
  float ethreshold = 0; /* Threshold value */
  int einterval = 0;    /* notification interval */
  int eduration = 0;    /* event duration */
  unsigned long elastnotification = 0; /* counts milliseconds since last notification */
  unsigned long estart = 0; /* counts miliseconds since trigger */
  bool etriggered = false;
  bool eset = false; /* is an event set by user in this space? */
  char automoperation[25] = "";
} event_proto;
 
//Sensor intervals (in seconds * 1000 to get milliseconds);
unsigned int moisture_interv = 30 * 1000;
unsigned long moisture_last = 0;
unsigned int rain_interv = 30 * 1000; // specification says minimum are 5 TIMEOUTs (300sec)
unsigned long rain_last = 0;
unsigned int bright_interv = 30 * 1000;
unsigned long bright_last = 0;
unsigned int temp_interv = 30 * 1000;
unsigned long temp_last = 0;
unsigned int pressure_interv = 30 * 1000;
unsigned long pressure_last = 0;
unsigned int humidity_interv = 30 * 1000;
unsigned long humidity_last = 0; 
// Sensor Measurements
float brightn = 0;
float moisture = 0;
float rain = 0;
float temp = 0;
float pressure = 0;
float humidity = 0;

// Actuator pump
/* Pumping is done for the specified amount, then the pump is automatically turned off again */
unsigned int pumping_time = 3 * 1000; 

// Wifi Connection
const char* ssid = "your-WIFI-name";
const char* password =  "WIFI-password";
//IP of the Raspberry Pi or PC with MQTT Broker 
const char* mqtt_server = "192.168.0.110";

WiFiClient Board1;
PubSubClient client(Board1);

// Sleeping time
// Ontology & Device UUID
// Device UUID and ontology with placeholder "%s" for UUID -> like Michael Nowak
String device_uuid = UUID;
// Device Ontology
String ontology ="{\"@context\": {\"owl\": \"http://www.w3.org/2002/07/owl#\",\"rdf\": \"http://www.w3.org/1999/02/22-rdf-syntax-ns#\",\"rdfs\": \"http://www.w3.org/2000/01/rdf-schema#\",\"xsd\": \"http://www.w3.org/2001/XMLSchema#\",\"base\": \"http://yang-netconf-mqtt#\",\"onem2m\": \"http://www.onem2m.org/ontology/Base_Ontology/base_ontology#\",\"om-2\": \"http://www.ontology-of-units-of-measure.org/resource/om-2/\",\"time\": \"http://www.w3.org/2006/time#\"},\"@graph\": [{\"@id\": \"onem2m:Command\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:ControllingFunctionality\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:Device\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:MeasuringFunctionality\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:Operation\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:OperationInput\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:OperationOutput\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:OperationState\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:OutputDataPoint\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:Service\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:ThingProperty\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:Variable\",\"@type\": \"owl:Class\"},{\"@id\": \"onem2m:cmdPump_1Off\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Command\"],\"onem2m:hasInput\": {\"@id\": \"base:uuidInput\"}},{\"@id\": \"onem2m:cmdPump_1On\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Command\"],\"onem2m:hasInput\": {\"@id\": \"base:uuidInput\"}},{\"@id\": \"onem2m:exposesCommand\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:exposesFunctionality\",\"@type\": \"owl:AnnotationProperty\"},{\"@id\": \"onem2m:funcDescHumidity\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"Get humidity from sensor\"},{\"@id\": \"onem2m:funcDescMoisture\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"Get moisture from sensor\"},{\"@id\": \"onem2m:funcDescPressure\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"Get pressure from sensor\"},{\"@id\": \"onem2m:funcDescPump_1Off\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"turn pump 1 off\"},{\"@id\": \"onem2m:funcDescPump_1On\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"turn pump 1 on\"},{\"@id\": \"onem2m:funcDescRainDetect\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"Get rain detection signal from sensor\"},{\"@id\": \"onem2m:funcDescTemperature\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"Get Temperature from sensor\"},{\"@id\": \"onem2m:funcGetHumidity\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:MeasuringFunctionality\"],\"onem2m:hasThingProperty\": {\"@id\": \"onem2m:funcDescHumidity\"}},{\"@id\": \"onem2m:funcGetMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:MeasuringFunctionality\"],\"onem2m:hasThingProperty\": {\"@id\": \"onem2m:funcDescMoisture\"}},{\"@id\": \"onem2m:funcGetPressure\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:MeasuringFunctionality\"],\"onem2m:hasThingProperty\": {\"@id\": \"onem2m:funcDescPressure\"}},{\"@id\": \"onem2m:funcGetRainDetect\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:MeasuringFunctionality\"],\"onem2m:hasThingProperty\": {\"@id\": \"onem2m:funcDescRainDetect\"}},{\"@id\": \"onem2m:funcGetTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:MeasuringFunctionality\"],\"onem2m:hasThingProperty\": {\"@id\": \"onem2m:funcDescTemperature\"}},{\"@id\": \"onem2m:funcPump_1Off\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ControllingFunctionality\"],\"onem2m:hasCommand\": {\"@id\": \"onem2m:cmdPump_1Off\"},\"onem2m:hasThingProperty\": {\"@id\": \"onem2m:funcDescPump_1Off\"}},{\"@id\": \"onem2m:funcPump_1On\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ControllingFunctionality\"],\"onem2m:hasCommand\": {\"@id\": \"onem2m:cmdPump_1On\"},\"onem2m:hasThingProperty\": {\"@id\": \"onem2m:funcDescPump_1On\"}},{\"@id\": \"onem2m:hasCommand\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:hasDataRestriction_maxInclusive\",\"@type\": \"owl:AnnotationProperty\"},{\"@id\": \"onem2m:hasDataRestriction_minInclusive\",\"@type\": \"owl:AnnotationProperty\"},{\"@id\": \"onem2m:hasDataRestriction_pattern\",\"@type\": \"owl:DatatypeProperty\"},{\"@id\": \"onem2m:hasDataType\",\"@type\": \"owl:AnnotationProperty\"},{\"@id\": \"onem2m:hasFunctionality\",\"@type\": \"owl:AnnotationProperty\"},{\"@id\": \"onem2m:hasInput\",\"@type\": \"owl:ObjectProperty\",\"rdfs:range\": {\"@id\": \"onem2m:ThingProperty\"}},{\"@id\": \"onem2m:hasOperation\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:hasOperationState\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:hasOutput\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:hasOutputDataPoint\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:hasService\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:hasSubService\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:hasSubStructure\",\"@type\": \"owl:AnnotationProperty\"},{\"@id\": \"onem2m:hasThingProperty\",\"@type\": \"owl:ObjectProperty\"},{\"@id\": \"onem2m:hasValue\",\"@type\": \"owl:DatatypeProperty\"},{\"@id\": \"onem2m:opMqttPump_1Off\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Operation\"],\"onem2m:exposesCommand\": {\"@id\": \"onem2m:cmdPump_1Off\"},\"onem2m:hasInput\": {\"@id\": \"base:uuidInput\"},\"onem2m:hasOperationState\": {\"@id\": \"base:opState\"},\"base:mqttMethod\": \"OFF\",\"base:mqttTopic\": \"actuator/pump/pump_1/%s\"},{\"@id\": \"onem2m:opMqttPump_1On\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Operation\"],\"onem2m:exposesCommand\": {\"@id\": \"onem2m:cmdPump_1On\"},\"onem2m:hasInput\": {\"@id\": \"base:uuidInput\"},\"onem2m:hasOperationState\": {\"@id\": \"base:opState\"},\"base:mqttMethod\": \"ON\",\"base:mqttTopic\": \"actuator/pump/pump_1/%s\"},{\"@id\": \"onem2m:outDpHumidity\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OutputDataPoint\"],\"om-2:hasUnit\": {\"@id\": \"om-2:percent\"},\"base:mqttTopic\": \"sensor/humidity/humidity_1/%s\"},{\"@id\": \"onem2m:outDpMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OutputDataPoint\"],\"om-2:hasUnit\": {\"@id\": \"om-2:percent\"},\"base:mqttTopic\": \"sensor/moisture/moisture_1/%s\"},{\"@id\": \"onem2m:outDpPressure\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OutputDataPoint\"],\"om-2:hasUnit\": {\"@id\": \"om-2:hectopascal\"},\"base:mqttTopic\": \"sensor/pressure/pressure_1/%s\"},{\"@id\": \"onem2m:outDpRainDetect\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OutputDataPoint\"],\"om-2:hasUnit\": {\"@id\": \"om-2:percent\"},\"base:mqttTopic\": \"sensor/rain/rain_1/%s\"},{\"@id\": \"onem2m:outDpTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OutputDataPoint\"],\"om-2:hasUnit\": {\"@id\": \"om-2:degreeCelsius\"},\"base:mqttTopic\": \"sensor/temperature/temperature_1/%s\"},{\"@id\": \"onem2m:servHumidity\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": {\"@id\": \"onem2m:funcGetHumidity\"},\"onem2m:hasOutputDataPoint\": {\"@id\": \"onem2m:outDpHumidity\"}},{\"@id\": \"onem2m:servMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": {\"@id\": \"onem2m:funcGetMoisture\"},\"onem2m:hasOutputDataPoint\": {\"@id\": \"onem2m:outDpMoisture\"}},{\"@id\": \"onem2m:servPressure\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": {\"@id\": \"onem2m:funcGetPressure\"},\"onem2m:hasOutputDataPoint\": {\"@id\": \"onem2m:outDpPressure\"}},{\"@id\": \"onem2m:servRainDetect\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": {\"@id\": \"onem2m:funcGetRainDetect\"},\"onem2m:hasOutputDataPoint\": {\"@id\": \"onem2m:outDpRainDetect\"}},{\"@id\": \"onem2m:servTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": {\"@id\": \"onem2m:funcGetTemperature\"},\"onem2m:hasOutputDataPoint\": {\"@id\": \"onem2m:outDpTemperature\"}},{\"@id\": \"om-2:degreeCelsius\",\"om-2:symbol\": \"°C\"},{\"@id\": \"om-2:hasUnit\",\"@type\": \"owl:AnnotationProperty\"},{\"@id\": \"om-2:hectopascal\",\"om-2:symbol\": \"hPa\"},{\"@id\": \"om-2:lux\",\"om-2:symbol\": \"lx\"},{\"@id\": \"om-2:percent\",\"om-2:symbol\": \"%%\"},{\"@id\": \"om-2:symbol\",\"@type\": \"owl:AnnotationProperty\"},{\"@id\": \"http://yang-netconf-mqtt\",\"@type\": \"owl:Ontology\",\"owl:imports\": [{\"@id\": \"http://www.w3.org/1999/02/22-rdf-syntax-ns#\"},{\"@id\": \"time:2016\"},{\"@id\": \"http://www.onem2m.org/ontology/Base_Ontology/base_ontology-v0_9_0\"},{\"@id\": \"http://www.ontology-of-units-of-measure.org/resource/om-2/\"}]},{\"@id\": \"base:AutomationFunctionality\",\"@type\": \"owl:Class\",\"rdfs:subClassOf\": {\"@id\": \"onem2m:Functionality\"}},{\"@id\": \"base:ConfigurationFunctionality\",\"@type\": \"owl:Class\",\"rdfs:subClassOf\": {\"@id\": \"onem2m:Functionality\"}},{\"@id\": \"base:EventFunctionality\",\"@type\": \"owl:Class\",\"rdfs:subClassOf\": {\"@id\": \"onem2m:Functionality\"}},{\"@id\": \"base:YangDescription\",\"@type\": \"owl:Class\",\"rdfs:subClassOf\": {\"@id\": \"onem2m:ThingProperty\"}},{\"@id\": \"base:autoMoistureYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"automation for moisture\"},{\"@id\": \"base:cmdAutoMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Command\"],\"onem2m:hasInput\": [{\"@id\": \"base:inputAutoMoisture\"},{\"@id\": \"base:uuidInput\"}]},{\"@id\": \"base:cmdConfMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Command\"],\"onem2m:hasInput\": [{\"@id\": \"base:input_1_ConfEvName\"},{\"@id\": \"base:input_2_ConfOperator\"},{\"@id\": \"base:input_3_ConfMoisture\"},{\"@id\": \"base:input_4_ConfInterval\"},{\"@id\": \"base:input_5_ConfDuration\"},{\"@id\": \"base:input_6_ConfCrud\"},{\"@id\": \"base:uuidInput\"}]},{\"@id\": \"base:cmdConfTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Command\"],\"onem2m:hasInput\": [{\"@id\": \"base:input_1_ConfEvName\"},{\"@id\": \"base:input_2_ConfOperator\"},{\"@id\": \"base:input_3_ConfTemperature\"},{\"@id\": \"base:input_4_ConfInterval\"},{\"@id\": \"base:input_5_ConfDuration\"},{\"@id\": \"base:input_6_ConfCrud\"},{\"@id\": \"base:uuidInput\"}]},{\"@id\": \"base:cmdLed_1Off\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Command\"],\"onem2m:hasInput\": {\"@id\": \"base:uuidInput\"}},{\"@id\": \"base:cmdLed_1On\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Command\"],\"onem2m:hasInput\": {\"@id\": \"base:uuidInput\"}},{\"@id\": \"base:cmdLed_1Rgb\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Command\"],\"onem2m:hasInput\": [{\"@id\": \"base:rgbinput\"},{\"@id\": \"base:uuidInput\"}]},{\"@id\": \"base:confOperatorYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"describes configuration operators\"},{\"@id\": \"base:crudYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"select CRUD operations for events\"},{\"@id\": \"base:deviceCategory\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ThingProperty\"],\"onem2m:hasValue\": \"%sBoardName\"},{\"@id\": \"base:deviceDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"MQTT-Device identified by UUID\"},{\"@id\": \"base:deviceUuid\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ThingProperty\"],\"onem2m:hasDataType\": {\"@id\": \"xsd:string\"},\"onem2m:hasValue\": \"%s\"},{\"@id\": \"base:durYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"duration for event configuration\"},{\"@id\": \"base:funcAutoMoisture\",\"@type\": [\"owl:NamedIndividual\",\"base:AutomationFunctionality\"],\"onem2m:hasCommand\": {\"@id\": \"base:cmdAutoMoisture\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescAutoMoisture\"}},{\"@id\": \"base:funcConfMoisture\",\"@type\": [\"owl:NamedIndividual\",\"base:ConfigurationFunctionality\"],\"onem2m:hasCommand\": {\"@id\": \"base:cmdConfMoisture\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescConfMoisture\"}},{\"@id\": \"base:funcConfTemperature\",\"@type\": [\"owl:NamedIndividual\",\"base:ConfigurationFunctionality\"],\"onem2m:hasCommand\": {\"@id\": \"base:cmdConfTemperature\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescConfTemperature\"}},{\"@id\": \"base:funcDescAutoMoisture\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"automation rule for moisture sensor\"},{\"@id\": \"base:funcDescBrightness\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"Get brightness from sensor\"},{\"@id\": \"base:funcDescConfMoisture\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"configure moisture sensor for events\"},{\"@id\": \"base:funcDescConfTemperature\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"configure event for temperature sensor\"},{\"@id\": \"base:funcDescEvMoisture\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"event function for moisture sensor\"},{\"@id\": \"base:funcDescEvTemperature\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"event function for temperature sensor\"},{\"@id\": \"base:funcDescLed_1Off\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"turn led 1 off\"},{\"@id\": \"base:funcDescLed_1On\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"turn led 1 on\"},{\"@id\": \"base:funcDescLed_1Rgb\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"set RGB values for led 1\"},{\"@id\": \"base:funcEvMoisture\",\"@type\": [\"owl:NamedIndividual\",\"base:EventFunctionality\"],\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescEvMoisture\"}},{\"@id\": \"base:funcEvTemperature\",\"@type\": [\"owl:NamedIndividual\",\"base:EventFunctionality\"],\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescEvTemperature\"}},{\"@id\": \"base:funcGetBrightness\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:MeasuringFunctionality\"],\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescBrightness\"}},{\"@id\": \"base:funcLed_1Off\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ControllingFunctionality\"],\"onem2m:hasCommand\": {\"@id\": \"base:cmdLed_1Off\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescLed_1Off\"}},{\"@id\": \"base:funcLed_1On\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ControllingFunctionality\"],\"onem2m:hasCommand\": {\"@id\": \"base:cmdLed_1On\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescLed_1On\"}},{\"@id\": \"base:funcLed_1Rgb\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ControllingFunctionality\"],\"onem2m:hasCommand\": {\"@id\": \"base:cmdLed_1Rgb\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:funcDescLed_1Rgb\"}},{\"@id\": \"base:inputAutoMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\"],\"onem2m:hasThingProperty\": {\"@id\": \"base:autoMoistureYangDesc\"}},{\"@id\": \"base:inputBlue\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Variable\"],\"onem2m:hasDataRestriction_maxInclusive\": {\"@type\": \"xsd:int\",\"@value\": \"255\"},\"onem2m:hasDataRestriction_minInclusive\": {\"@type\": \"xsd:int\",\"@value\": \"0\"}},{\"@id\": \"base:inputGreen\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Variable\"],\"onem2m:hasDataRestriction_maxInclusive\": {\"@type\": \"xsd:int\",\"@value\": \"255\"},\"onem2m:hasDataRestriction_minInclusive\": {\"@type\": \"xsd:int\",\"@value\": \"0\"}},{\"@id\": \"base:inputRed\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Variable\"],\"onem2m:hasDataRestriction_maxInclusive\": {\"@type\": \"xsd:int\",\"@value\": \"255\"},\"onem2m:hasDataRestriction_minInclusive\": {\"@type\": \"xsd:int\",\"@value\": \"0\"}},{\"@id\": \"base:input_1_ConfEvName\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\"],\"onem2m:hasInput\": {\"@id\": \"base:propConfEvName\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:temperatureEvYangDesc\"}},{\"@id\": \"base:input_2_ConfOperator\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\"],\"onem2m:hasDataRestriction_pattern\": [\"<\",\"<=\",\"==\",\">\",\">=\"],\"onem2m:hasThingProperty\": {\"@id\": \"base:confOperatorYangDesc\"}},{\"@id\": \"base:input_3_ConfMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\"],\"onem2m:hasInput\": {\"@id\": \"base:propConfMoisture\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:moistureYangDesc\"}},{\"@id\": \"base:input_3_ConfTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\"],\"onem2m:hasInput\": {\"@id\": \"base:propConfTemperature\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:temperatureYangDesc\"}},{\"@id\": \"base:input_4_ConfInterval\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\",\"time:Interval\"],\"onem2m:hasInput\": {\"@id\": \"base:propConfInterval\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:intervallYangDesc\"}},{\"@id\": \"base:input_5_ConfDuration\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\",\"time:Duration\"],\"onem2m:hasInput\": {\"@id\": \"base:propConfDuration\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:durYangDesc\"}},{\"@id\": \"base:input_6_ConfCrud\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\"],\"onem2m:hasDataRestriction_pattern\": [\"CREATE\",\"DELETE\",\"READ\",\"UPDATE\"],\"onem2m:hasThingProperty\": {\"@id\": \"base:crudYangDesc\"}},{\"@id\": \"base:intervallYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"interval for event configuration\"},{\"@id\": \"base:moistureEvYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"event name caused by configuration\"},{\"@id\": \"base:moistureYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"threshold values for moisture sensor\"},{\"@id\": \"base:mqttMethod\",\"@type\": \"owl:DatatypeProperty\"},{\"@id\": \"base:mqttTopic\",\"@type\": \"owl:DatatypeProperty\"},{\"@id\": \"base:myDevice\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Device\"],\"onem2m:hasFunctionality\": [{\"@id\": \"onem2m:funcGetHumidity\"},{\"@id\": \"onem2m:funcGetMoisture\"},{\"@id\": \"onem2m:funcGetPressure\"},{\"@id\": \"onem2m:funcGetRainDetect\"},{\"@id\": \"onem2m:funcGetTemperature\"},{\"@id\": \"onem2m:funcPump_1Off\"},{\"@id\": \"onem2m:funcPump_1On\"},{\"@id\": \"base:funcAutoMoisture\"},{\"@id\": \"base:funcConfMoisture\"},{\"@id\": \"base:funcConfTemperature\"},{\"@id\": \"base:funcEvMoisture\"},{\"@id\": \"base:funcEvTemperature\"},{\"@id\": \"base:funcGetBrightness\"},{\"@id\": \"base:funcLed_1Off\"},{\"@id\": \"base:funcLed_1On\"},{\"@id\": \"base:funcLed_1Rgb\"}],\"onem2m:hasService\": {\"@id\": \"base:servNetconf\"},\"onem2m:hasThingProperty\": [{\"@id\": \"base:deviceCategory\"},{\"@id\": \"base:deviceDesc\"},{\"@id\": \"base:deviceUuid\"}]},{\"@id\": \"base:opDescState\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasDataRestriction_pattern\": [\"error\",\"nothing to do\",\"successful\"]},{\"@id\": \"base:opMqttAutoMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Operation\"],\"onem2m:exposesCommand\": {\"@id\": \"base:cmdAutoMoisture\"},\"onem2m:hasInput\": [{\"@id\": \"base:inputAutoMoisture\"},{\"@id\": \"base:uuidInput\"}],\"onem2m:hasOperationState\": {\"@id\": \"base:opState\"},\"base:mqttMethod\": \"AUTOMATION\",\"base:mqttTopic\": \"automation/sensor/moisture/moisture_1/%s\" },{\"@id\": \"base:opMqttConfMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Operation\"],\"onem2m:exposesCommand\": {\"@id\": \"base:cmdConfMoisture\"},\"onem2m:hasInput\": [{\"@id\": \"base:input_1_ConfEvName\"},{\"@id\": \"base:input_2_ConfOperator\"},{\"@id\": \"base:input_3_ConfMoisture\"},{\"@id\": \"base:input_4_ConfInterval\"},{\"@id\": \"base:input_5_ConfDuration\"},{\"@id\": \"base:input_6_ConfCrud\"},{\"@id\": \"base:uuidInput\"}],\"onem2m:hasOperationState\": {\"@id\": \"base:opState\"},\"base:mqttMethod\": \"CONFIGEVENT\",\"base:mqttTopic\": \"config/sensor/moisture/moisture_1/%s\"},{\"@id\": \"base:opMqttConfTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Operation\"],\"onem2m:exposesCommand\": {\"@id\": \"base:cmdConfTemperature\"},\"onem2m:hasInput\": [{\"@id\": \"base:input_1_ConfEvName\"},{\"@id\": \"base:input_2_ConfOperator\"},{\"@id\": \"base:input_3_ConfTemperature\"},{\"@id\": \"base:input_4_ConfInterval\"},{\"@id\": \"base:input_5_ConfDuration\"},{\"@id\": \"base:input_6_ConfCrud\"},{\"@id\": \"base:uuidInput\"}],\"onem2m:hasOperationState\": {\"@id\": \"base:opState\"},\"base:mqttMethod\": \"CONFIGEVENT\",\"base:mqttTopic\": \"config/sensor/temperature/temperature_1/%s\"},{\"@id\": \"base:opMqttLed_1Off\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Operation\"],\"onem2m:exposesCommand\": {\"@id\": \"base:cmdLed_1Off\"},\"onem2m:hasInput\": {\"@id\": \"base:uuidInput\"},\"onem2m:hasOperationState\": {\"@id\": \"base:opState\"},\"base:mqttMethod\": \"OFF\",\"base:mqttTopic\": \"actuator/led/led_1/%s\"},{\"@id\": \"base:opMqttLed_1On\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Operation\"],\"onem2m:exposesCommand\": {\"@id\": \"base:cmdLed_1On\"},\"onem2m:hasInput\": {\"@id\": \"base:uuidInput\"},\"onem2m:hasOperationState\": {\"@id\": \"base:opState\"},\"base:mqttMethod\": \"ON\",\"base:mqttTopic\": \"actuator/led/led_1/%s\"},{\"@id\": \"base:opMqttLed_1Rgb\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Operation\"],\"onem2m:exposesCommand\": {\"@id\": \"base:cmdLed_1Rgb\"},\"onem2m:hasInput\": [{\"@id\": \"base:rgbinput\"},{\"@id\": \"base:uuidInput\"}],\"onem2m:hasOperationState\": {\"@id\": \"base:opState\"},\"base:mqttMethod\": \"RGB\",\"base:mqttTopic\": \"actuator/led/led_1/%s\"},{\"@id\": \"base:opState\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationState\"],\"onem2m:hasDataRestriction_pattern\": [\"ERROR\",\"NOOP\",\"OK\"],\"onem2m:hasThingProperty\": {\"@id\": \"base:opDescState\"}},{\"@id\": \"base:outDpBrightness\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OutputDataPoint\"],\"om-2:hasUnit\": {\"@id\": \"om-2:lux\"},\"base:mqttTopic\": \"sensor/brightness/brightness_1/%s\"},{\"@id\": \"base:outDpEvMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OutputDataPoint\"],\"base:mqttTopic\": \"event/sensor/moisture/moisture_1/%s\"},{\"@id\": \"base:outDpEvTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OutputDataPoint\"],\"base:mqttTopic\": \"event/sensor/temperature/temperature_1/%s\"},{\"@id\": \"base:propConfDuration\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ThingProperty\"],\"onem2m:hasDataType\": {\"@id\": \"xsd:int\"}},{\"@id\": \"base:propConfEvName\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ThingProperty\"],\"onem2m:hasDataType\": {\"@id\": \"xsd:string\"}},{\"@id\": \"base:propConfInterval\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ThingProperty\"],\"onem2m:hasDataType\": {\"@id\": \"xsd:int\"}},{\"@id\": \"base:propConfMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ThingProperty\"],\"onem2m:hasDataRestriction_maxInclusive\": \"100\",\"onem2m:hasDataRestriction_minInclusive\": \"0\",\"onem2m:hasDataType\": {\"@id\": \"xsd:int\"}},{\"@id\": \"base:propConfTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:ThingProperty\"],\"onem2m:hasDataRestriction_maxInclusive\": {\"@type\": \"xsd:integer\",\"@value\": \"100\"},\"onem2m:hasDataRestriction_minInclusive\": {\"@type\": \"xsd:integer\",\"@value\": \"-20\"},\"onem2m:hasDataType\": {\"@id\": \"xsd:int\"}},{\"@id\": \"base:rgbYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"RGB parameter for led_1\"},{\"@id\": \"base:rgbinput\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\"],\"onem2m:hasSubStructure\": [{\"@id\": \"base:inputBlue\"},{\"@id\": \"base:inputGreen\"},{\"@id\": \"base:inputRed\"}],\"onem2m:hasThingProperty\": {\"@id\": \"base:rgbYangDesc\"}},{\"@id\": \"base:servBrightness\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": {\"@id\": \"base:funcGetBrightness\"},\"onem2m:hasOutputDataPoint\": {\"@id\": \"base:outDpBrightness\"}},{\"@id\": \"base:servEvMoisture\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": {\"@id\": \"base:funcEvMoisture\"},\"onem2m:hasOutputDataPoint\": {\"@id\": \"base:outDpEvMoisture\"}},{\"@id\": \"base:servEvTemperature\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": {\"@id\": \"base:funcEvTemperature\"},\"onem2m:hasOutputDataPoint\": {\"@id\": \"base:outDpEvTemperature\"}},{\"@id\": \"base:servNetconf\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:Service\"],\"onem2m:exposesFunctionality\": [{\"@id\": \"onem2m:funcGetHumidity\"},{\"@id\": \"onem2m:funcGetMoisture\"},{\"@id\": \"onem2m:funcGetPressure\"},{\"@id\": \"onem2m:funcGetRainDetect\"},{\"@id\": \"onem2m:funcGetTemperature\"},{\"@id\": \"onem2m:funcPump_1Off\"},{\"@id\": \"onem2m:funcPump_1On\"},{\"@id\": \"base:funcAutoMoisture\"},{\"@id\": \"base:funcConfMoisture\"},{\"@id\": \"base:funcConfTemperature\"},{\"@id\": \"base:funcEvMoisture\"},{\"@id\": \"base:funcEvTemperature\"},{\"@id\": \"base:funcGetBrightness\"},{\"@id\": \"base:funcLed_1Off\"},{\"@id\": \"base:funcLed_1On\"},{\"@id\": \"base:funcLed_1Rgb\"}],\"onem2m:hasOperation\": [{\"@id\": \"onem2m:opMqttPump_1Off\"},{\"@id\": \"onem2m:opMqttPump_1On\"},{\"@id\": \"base:opMqttAutoMoisture\"},{\"@id\": \"base:opMqttConfMoisture\"},{\"@id\": \"base:opMqttConfTemperature\"},{\"@id\": \"base:opMqttLed_1Off\"},{\"@id\": \"base:opMqttLed_1On\"},{\"@id\": \"base:opMqttLed_1Rgb\"}],\"onem2m:hasSubService\": [{\"@id\": \"onem2m:servHumidity\"},{\"@id\": \"onem2m:servMoisture\"},{\"@id\": \"onem2m:servPressure\"},{\"@id\": \"onem2m:servRainDetect\"},{\"@id\": \"onem2m:servTemperature\"},{\"@id\": \"base:servBrightness\"},{\"@id\": \"base:servEvMoisture\"},{\"@id\": \"base:servEvTemperature\"}]},{\"@id\": \"base:temperatureEvYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"event name caused by configuration\"},{\"@id\": \"base:temperatureYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"threshold values for temperature sensor\"},{\"@id\": \"base:uuidInput\",\"@type\": [\"owl:NamedIndividual\",\"onem2m:OperationInput\"],\"onem2m:hasInput\": {\"@id\": \"base:deviceUuid\"},\"onem2m:hasThingProperty\": {\"@id\": \"base:uuidYangDesc\"}},{\"@id\": \"base:uuidYangDesc\",\"@type\": [\"owl:NamedIndividual\",\"base:YangDescription\"],\"onem2m:hasValue\": \"Target UUID for request\"}]}";
// Ontology Crud variables
bool device_isknown = false;
bool got_crud_response = false;
bool checkout_successful = false;
int tries = 0; 

// DEEP SLEEP:
// saved in deep sleep
RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR event_proto moisture1_events[NUMBER_OF_EVENTS];
RTC_DATA_ATTR event_proto temperature1_events[NUMBER_OF_EVENTS];
RTC_DATA_ATTR int active_events_num = 0;

// Sensors
BH1750 brightness_1;
Adafruit_BME280 hum_pres_temp_1;
const int brightness_scl = 21;
const int brightness_sda = 22;
const int moisture_out = 33;
const int rain_out = 32;
// Actuators
const int led_1r = 17; //25;
const int led_1g = 18; //26;
const int led_1b = 19; //27;
const int pump_1 = 25; //18, rewired;
// global to remember old values 
int rval, gval, bval = 0;


//Setup includes: Wifi and MQTT Conncection, Setting up Sensors, Publishing Device Description
void setup(){
  delay(500);
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  #ifdef DEBUG
  Serial.begin(115200);
  #endif
  if (bootCount == 0){
    #ifdef DEBUG
    Serial.println("Starting Sketch");
    Serial.println("Heap info");
    Serial.println(ESP.getMaxAllocHeap());
    #endif
  }
  ++bootCount;
  generate_config();
  setup_wifi(); 
  setup_mqtt();
  setup_sensors();
  setup_actuators();
  if (bootCount == 1){
    //publish_config(CREATE_TOPIC_P);
    device_configuration("create");
  }
  else {
    #ifdef DEBUG  
    Serial.println("Device woken up");
    Serial.print("Boot number: ");
    Serial.println(bootCount);
    #endif
    #ifdef CRUD_SLEEP
    device_configuration("update");
    //device_configuration("delete");
    if(!device_isknown){
      device_configuration("create");
    }
    #endif
  } 
  out_brightness_1();
  out_temp_1();
  out_humidity_1();
  out_pressure_1();
  out_moisture_1();
  out_rain_1();
} /* end setup */

//Connect to Wifi
void setup_wifi() {
  #ifdef DEBUG
  Serial.println();   
  Serial.println("Attempting Wifi-Connection: ");
  #endif
  delay(10);
  unsigned long starttime = millis();
  // We start by connecting to a WiFi network
  #ifdef DEBUG
  Serial.print("Attempting WiFi connection to: ");
  Serial.println(ssid);
  #endif
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED && (millis()-starttime) < TIMEOUT) {
     #ifdef DEBUG
     delay(100);
     Serial.print(".");
     #endif
  }
  if (WiFi.status() != WL_CONNECTED) {
    #ifdef DEBUG
    Serial.println("");
    Serial.println("Unable to attain Wifi connection, going to sleep, press rst to start again.");
    #endif
    esp_deep_sleep_start();
  }
  #ifdef DEBUG
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  #endif
} /* end setup_wifi */

//Connection to MQTT
void setup_mqtt(){
    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);
    unsigned long starttime = millis();
    #ifdef DEBUG
    Serial.println();
    Serial.println("Attempting MQTT-Connection: ");
    #endif
    while (!client.connected() && (millis()-starttime) < TIMEOUT) {
        #ifdef DEBUG
        Serial.print(".");
        #endif
        // Attempt to connect
        if (client.connect(UUID)) {
          break;
        } 
        else {
          #ifdef DEBUG
          Serial.print("failed, response code: ");
          Serial.print(client.state());
          Serial.println(" trying again in 5 seconds");
          #endif
          // Wait 5 seconds before retrying
          //delay(5000);
          #ifdef DEBUG
          Serial.println("Attempting MQTT-Connection: ");
          #endif
        }
    }
    if(!client.connected()){
      #ifdef DEBUG
       Serial.println("Unable to attain MQTT connection, going to sleep, press rst to start again.");
       #endif
       esp_deep_sleep_start();
    }
    #ifdef DEBUG
    Serial.println("MQTT connected.");
    #endif
    client.subscribe(LED1_TOPIC_S);
    client.subscribe(PUMP1_TOPIC_S);
    #ifdef DEBUG
    Serial.println("Subscribed to: "LED1_TOPIC_S);
    #endif
    client.subscribe(CREATE_TOPIC_S);
    client.subscribe(RETRIEVE_TOPIC_S);
    client.subscribe(UPDATE_TOPIC_S);
    client.subscribe(DELETE_TOPIC_S);
    #ifdef DEBUG
    Serial.println("Subscribed to CRUD Topics: "CRUD_TOPICS_S);
    #endif
    client.subscribe(PING_TOPIC_S);
    #ifdef DEBUG
    Serial.println("Subscribed to PING Topic: "PING_TOPIC_S);
    #endif
    client.subscribe(SENSOR_CONFIG_S);
    client.subscribe(SENSOR_AUTOM_S);
} /* end setup MQTT */

/* This function is used to do crud operations regarding the ontology with mqtt bridge */
void device_configuration(char* operation){
  // OPERATION: CREATE; RETRIEVE; UPDATE; DELETE
  // FIRST IS ALWAYS RETRIEVE
  device_isknown = false;
  client.publish(RETRIEVE_TOPIC_P,UUID);
  crud_response_wait("retrieve");
  if (strcmp(operation,"create") == 0){ 
    if(device_isknown){
      #ifdef DEBUG
      Serial.println("Aborting Configuration Publication. Device already known. Updating instead.");
      #endif
      publish_config(UPDATE_TOPIC_P);
      crud_response_wait("update");
    }
    else{
      publish_config(CREATE_TOPIC_P);
      crud_response_wait("create");
    }
  }
  else if (strcmp(operation,"retrieve") == 0){
    // Read is performed first
  }
  else if (strcmp(operation,"update") == 0){
    if(device_isknown){
      publish_config(UPDATE_TOPIC_P);
      crud_response_wait("update");
    }
    else{
      #ifdef DEBUG
      Serial.println("Device unknown, publishing config instead");
      #endif
      publish_config(CREATE_TOPIC_P);
      crud_response_wait("create");
    }
  }
  else if (strcmp(operation,"delete") == 0){
    if(device_isknown){
      client.publish(DELETE_TOPIC_P,UUID);
      crud_response_wait("delete");
    }
  else{
      #ifdef DEBUG
      Serial.println("Device unknown, deletion impossible");
      #endif
    }
  }
} /* end device_configuration()*/

// Wait for response to CRUD-Request before moving forward
void crud_response_wait(char* Operation){
   got_crud_response = false;
   unsigned long starttime = millis();
   while(tries < 5){
     while(!got_crud_response && (millis()-starttime) < TIMEOUT){
      if(!client.connected()){
        if(WiFi.status() != WL_CONNECTED){
          setup_wifi();
        }
        setup_mqtt();
        tries = 0;
        device_configuration(Operation);
      }
      #ifdef DEBUG
      Serial.print("Waiting for CRUD-Reponse for: ");
      Serial.println(Operation);
      delay(1000);
      #endif
      client.loop();
     }
   if(got_crud_response){
    return;
   }
   else{
    tries++;
    device_configuration(Operation);
   }
  }
  char *msg;
  sprintf(msg,UUID" %s",Operation);
  client.publish(ERROR_P,msg);
} /* end crud_response_wait */


void generate_config(){
  // Replace %s with device uuid and concatenate device uuid and ontology
  ontology.replace("%sBoardName",BOARD);
  ontology.replace("%s",UUID);
  // for two part ontology
  /*ontology_1.replace("%sBoardName",BOARD);
  ontology_2.replace("%sBoardName",BOARD);
  ontology_1.replace("%s",UUID);
  ontology_2.replace("%s",UUID);*/
  #ifdef DEBUG
  Serial.println("Replaced placeholder with UUID");
  #endif
}

// Publication of Device Description called within device_configuration
void publish_config(char* topic){
  #ifdef DEBUG
  Serial.println();   
  Serial.println("Publishing Device Description: ");  
  #endif
  client.publish(topic,String(device_uuid+";"+ontology).c_str());
  // two part publish
  /*client.publish(topic,String(device_uuid+";"+ontology_1).c_str());
  client.publish(topic,String(device_uuid+";"+ontology_2).c_str());*/
  // Create END-Message for configuration and send
  //String(device_uuid+";END").toCharArray(configuration_end,sizeof(configuration_end));
  client.publish(topic,UUID";END");
  #ifdef DEBUG
  Serial.println("Ontology published.");
  #endif
}

void setup_sensors(){
   // Sensors are defined globally
   // BH1750: brigthness_1
   // Wire.begin takes two parameters: SDA pin and SCL pin;
   Wire.begin(brightness_sda,brightness_scl);
   // bme280 has to be given specific address and Wire object (SDA/SCL) pin from before)
   hum_pres_temp_1.begin(0x76, &Wire); 
   #ifdef DEBUG
   Serial.println("BME280 Set up");
   #endif
   brightness_1.begin(BH1750::ONE_TIME_HIGH_RES_MODE_2);
   #ifdef DEBUG
   Serial.println("BH1750 High Resolution Mode");
   #endif
}
/* Sensor measurements: parameters like bright_last, temp_last are used for ensuring certain measurement intervals. 
   For now these are hard-coded*/

// Measure brightness and publish 
void out_brightness_1(){
  char lux_msg[15];
  brightn =  brightness_1.readLightLevel();
  /*Sometimes old values get published, maybe takes a little longer*/
  delay(100);
  sprintf(lux_msg, "%.1f", brightn);
  client.publish(BRIGHT1_TOPIC_P, lux_msg);
  bright_last = millis();

}
// Measure temperature and publish 
void out_temp_1(){
  /* see documentation for setup of bme sensor */
  hum_pres_temp_1.setSampling(Adafruit_BME280::MODE_FORCED,
                    Adafruit_BME280::SAMPLING_X1, // temperature
                    Adafruit_BME280::SAMPLING_X1, // pressure
                    Adafruit_BME280::SAMPLING_X1, // humidity
                    Adafruit_BME280::FILTER_OFF   );
  char temp_msg[15];
  temp = hum_pres_temp_1.readTemperature();
  #ifdef DEBUG
  Serial.print("Temperature: ");
  Serial.println(temp);
  #endif
  sprintf(temp_msg, "%.2f", temp);
  client.publish(TEMP1_TOPIC_P, temp_msg);
  temp_last = millis();
}
// Measure pressure and publish 
void out_pressure_1(){
  hum_pres_temp_1.setSampling(Adafruit_BME280::MODE_FORCED,
                    Adafruit_BME280::SAMPLING_X1, // temperature
                    Adafruit_BME280::SAMPLING_X1, // pressure
                    Adafruit_BME280::SAMPLING_X1, // humidity
                    Adafruit_BME280::FILTER_OFF   );
  char pressure_msg[15];
  pressure = hum_pres_temp_1.readPressure()/100.00;
  sprintf(pressure_msg, "%.2f", pressure);
  client.publish(PRES1_TOPIC_P, pressure_msg);
  pressure_last = millis();
}

// Measure humidity and publish 
void out_humidity_1(){
  hum_pres_temp_1.setSampling(Adafruit_BME280::MODE_FORCED,
                    Adafruit_BME280::SAMPLING_X1, // temperature
                    Adafruit_BME280::SAMPLING_X1, // pressure
                    Adafruit_BME280::SAMPLING_X1, // humidity
                    Adafruit_BME280::FILTER_OFF   );
  char humidity_msg[15];
  humidity = hum_pres_temp_1.readHumidity();
  sprintf(humidity_msg, "%.2f", humidity);    
  client.publish(HUM1_TOPIC_P, humidity_msg);
  humidity_last = millis();
}

/* Measure rain and publish: Note Analog sensor values for dry and rain have to
 *  be measured using calibration scripts: see documentation. The measured value is then
 *  converted to percent.
 */
void out_rain_1(){
  char rain_msg[15];
  int rain_analog = analogRead(rain_out);
  rain = float(100) - float(rain_analog-RAIN_WET) / float(RAIN_DRY-RAIN_WET) * 100;
  if (rain > 100){
    rain = 100;
  }
  #ifdef DEBUG
  Serial.print("Rain ");
  Serial.println(rain);
  #endif
  sprintf(rain_msg, "%.2f", rain);
  client.publish(RAIN1_TOPIC_P, rain_msg);
  rain_last = millis();
}
/* Measure moisture and publish: Note Analog sensor values for dry and rain have to
 *  be measured using calibration scripts: see documentation. The measured value is then
 *  converted to percent.
 */
void out_moisture_1(){
    char moisture_msg[15];
    int moisture_analog = analogRead(moisture_out);
    Serial.print("Moisture analog ");
    Serial.println(moisture_analog);
    moisture = float(100) - float(moisture_analog-MOISTURE_WATER) / float(MOISTURE_AIR-MOISTURE_WATER) * 100;
    if (moisture > 100){
      moisture = 100;
    }
    #ifdef DEBUG
    Serial.print("Moisture ");
    Serial.println(moisture);
    #endif
    sprintf(moisture_msg, "%.2f", moisture);
    client.publish(MOIST1_TOPIC_P,moisture_msg);
    moisture_last = millis();
}

/* Setup of actuators, for setup details of rgb led see documentation */
void setup_actuators(){
  ledcAttachPin(led_1r, 1); // assign RGB led pins to channels
  ledcAttachPin(led_1g, 2);
  ledcAttachPin(led_1b, 3);
  
  // Initialize channels 
  // channels 0-15, resolution 1-16 bits, freq limits depend on resolution
  // ledcSetup(uint8_t channel, uint32_t freq, uint8_t resolution_bits);
  ledcSetup(1, 12000, 8); // 12 kHz PWM, 8-bit resolution (256 values!)
  ledcSetup(2, 12000, 8);
  ledcSetup(3, 12000, 8);
  ledcWrite(1,0);
  ledcWrite(2,0);
  ledcWrite(3,0); 
  // setup Pump
  pinMode(pump_1,OUTPUT);
  digitalWrite(pump_1,LOW);
}

// Callback function used for subscribed topics
void callback(char* topic, byte* message_bytes, unsigned int length) {
  // Retrieve message and commands + parameters
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)message_bytes[i];
  }
  #ifdef DEBUG
  Serial.print(topic);
  //Serial.print(". Message: ");
  Serial.println(message);
  #endif
  // Retrieve parts of message: For RPC seq_id is a message id, otherwise the first part of the message is the command. 
  char *seq_id, *cmd, *cmd_param, *response;
  char reponse_error[20];
  const char delim[] = ";";
  seq_id = strtok((char*)message.c_str(),delim);
  #ifdef DEBUG
  Serial.print("Message id: ");
  Serial.println(seq_id);
  #endif
  cmd = strtok(NULL,delim);
  if (cmd == NULL){
    cmd = seq_id;
    seq_id = "none";
  }
  #ifdef DEBUG
  Serial.print("Command: ");
  Serial.println(cmd);
  #endif
  cmd_param = strtok(NULL,delim);
  if (cmd_param == NULL){
    cmd_param = "none";
  }
  #ifdef DEBUG
  Serial.print("Command Parameter: ");
  Serial.println(cmd_param);
  #endif
  
  // DIFFERENT TOPICS
  if (strcmp(topic, CREATE_TOPIC_S) == 0){
     create_react(cmd);
  }
  else if (strcmp(topic, RETRIEVE_TOPIC_S) == 0){
     read_react(cmd);
  }
  else if (strcmp(topic, UPDATE_TOPIC_S) == 0){
     update_react(cmd);
  }
  else if (strcmp(topic, DELETE_TOPIC_S) == 0){
     delete_react(cmd);
  }
  else if (strcmp(topic,PING_TOPIC_S) == 0){
    #ifdef DEBUG
    Serial.println("Got ping request");
    #endif
    ping_response();
  }
  else if (strstr(topic,"led_1") != NULL){
    #ifdef DEBUG
    Serial.println("Command for LED1");
    #endif
    response = led_1_response(cmd,cmd_param, seq_id);
    publish_response(RESPONSE_TOPIC_P,response);
  }
  else if (strstr(topic,"pump_1") != NULL){
    #ifdef DEBUG
    Serial.println("Command for Pump1");
    #endif
    response = pump_1_response(cmd,cmd_param, seq_id);
    publish_response(RESPONSE_TOPIC_P,response);
  }
  /* SENSOR CONFIGURATION: SO FAR ONLY EVENTS/AUTOMATION FOR TEMP/MOISTURE
  /*else if (strcmp(topic,BRIGHT1_CONFIG) == 0){
      if (strcmp(cmd,"interval") == 0){
        response = sensor_config_interval(topic, cmd, cmd_param,seq_id,bright_interv);
         publish_response(RESPONSE_TOPIC_P,response);
      }
      else {
        sprintf(reponse_error,"%s;ERROR",seq_id);
        publish_response(RESPONSE_TOPIC_P,reponse_error);
      }
   }*/
  else if (strcmp(topic,TEMP1_CONFIG) == 0){
    if(strcmp(cmd,"CONFIGEVENT") == 0){
      response = event_crud(seq_id,cmd_param,temperature1_events,TEMP1_TOPIC_EVENT,cmd);
      #ifdef DEBUG
      Serial.println("Sending Response for event configuration");
      #endif
      publish_response(RESPONSE_TOPIC_P,response);
    }
    /*else if (strcmp(cmd,"interval") == 0){
      response = sensor_config_interval(topic, cmd, cmd_param,seq_id,temp_interv);
      publish_response(RESPONSE_TOPIC_P,response);
    }*/
    else {
      sprintf(reponse_error,"%s;ERROR",seq_id);
      publish_response(RESPONSE_TOPIC_P,reponse_error);
    }
  }
  /*else if (strcmp(topic,PRES1_CONFIG) == 0){
      if (strcmp(cmd,"interval") == 0){
        response = sensor_config_interval(topic, cmd, cmd_param,seq_id,pressure_interv);
        publish_response(RESPONSE_TOPIC_P,response);
      }
      else {
        sprintf(reponse_error,"%s;ERROR",seq_id);
        publish_response(RESPONSE_TOPIC_P,reponse_error);
      }
    }*/
  /*else if (strcmp(topic,HUM1_CONFIG) == 0){
      if (strcmp(cmd,"interval") == 0){
        response = sensor_config_interval(topic, cmd, cmd_param,seq_id,humidity_interv);
        publish_response(RESPONSE_TOPIC_P,response);
      }
      else {
        sprintf(reponse_error,"%s;ERROR",seq_id);
        publish_response(RESPONSE_TOPIC_P,reponse_error);
      }
    }*/
  else if (strcmp(topic,MOIST1_CONFIG) == 0){
    if(strcmp(cmd,"CONFIGEVENT") == 0){
      response = event_crud(seq_id,cmd_param,moisture1_events,MOIST1_TOPIC_EVENT,cmd);
      publish_response(RESPONSE_TOPIC_P,response);
    }
    /*else if (strcmp(cmd,"interval") == 0){
      response = sensor_config_interval(topic, cmd, cmd_param,seq_id,moisture_interv);
      publish_response(RESPONSE_TOPIC_P,response);
    }*/
    else {
      sprintf(reponse_error,"%s;ERROR",seq_id);
      publish_response(RESPONSE_TOPIC_P,reponse_error);
    }
  }
  else if (strcmp(topic,MOIST1_AUTOM) == 0){
    if (strcmp(cmd,"AUTOMATION") == 0){
      response = event_crud(seq_id,cmd_param,moisture1_events,MOIST1_TOPIC_EVENT,cmd);
      publish_response(RESPONSE_TOPIC_P,response);
    }
    else {
      sprintf(reponse_error,"%s;ERROR",seq_id);
      publish_response(RESPONSE_TOPIC_P,reponse_error);
    }
  }
  /*else if (strcmp(topic,RAIN1_CONFIG) == 0){
    if (strcmp(cmd,"interval") == 0){
      response = sensor_config_interval(topic, cmd, cmd_param,seq_id,rain_interv);
      publish_response(RESPONSE_TOPIC_P,response);
    } 
    else {
      sprintf(reponse_error,"%s;ERROR",seq_id);
      publish_response(RESPONSE_TOPIC_P,reponse_error);
    }
  }*/
  else {
    #ifdef DEBUG
    Serial.println("Topic unknown");
    #endif
    sprintf(reponse_error,"%s;ERROR",seq_id);
    publish_response(RESPONSE_TOPIC_P,reponse_error);
  }
} /* end callback function */

void ping_response(){
  client.publish(PING_TOPIC_P,CRUD_OK);
  /*char reply[50];
  sprintf(reply,"%s;"CRUD_OK,seq_id);
  publish_response(PING_TOPIC_P,reply);*/
}

/* This function reacts to bridge messages regarding CRUD create. Input from callback function */
void create_react(char* cmd){
      if (strcmp(cmd,CRUD_OK) == 0 ){
        #ifdef DEBUG
        Serial.println("Device config successfully sent");
        #endif
      }
      else {
        #ifdef DEBUG
        Serial.println("Error sending device config"); 
        #endif
      }
      got_crud_response = true;      
}
/* This function reacts to bridge messages regarding CRUD read */
void read_react(char* cmd){
     if (strcmp(cmd,CRUD_OK) == 0 ){
        #ifdef DEBUG
        Serial.println("Device config known");
        #endif
        device_isknown = true;
      }
      else {
        #ifdef DEBUG
        Serial.println("Device config not known"); 
        #endif
      }    
      got_crud_response = true;      
}
/* This function reacts to bridge messages regarding CRUD delete. Input from callback function */
void delete_react(char* cmd){
      if (strcmp(cmd,CRUD_OK) == 0 ){
        #ifdef DEBUG
        Serial.println("Device config deletion successful");
        #endif
        checkout_successful = true;
      }
      else {
        #ifdef DEBUG
        Serial.println("Device config deletion not successful"); 
        #endif
      }    
      got_crud_response = true;      
}
/* This function reacts to bridge messages regarding CRUD update. Input from callback function */
void update_react(char* cmd){
      if (strcmp(cmd,CRUD_OK) == 0 ){
        #ifdef DEBUG
        Serial.println("Device config update successful");
        #endif
      }
      else {
        #ifdef DEBUG
        Serial.println("Device config update not successful"); 
        #endif
      }    
      got_crud_response = true;     
}


// Changes in LED1: Input command and command parameters and message id all from callback function, output: response message
char* led_1_response(char* command, char* command_param, char* seq_id){
  static char reply[20];
  if (strcmp(command,"ON") == 0) {
    #ifdef DEBUG
    Serial.println("Command ON");
    #endif
    if (rval == 255 &&  gval == 255 && bval == 255){
        sprintf(reply,"%s;NOOP",seq_id);

    }
    else {
      ledcWrite(1,255);
      ledcWrite(2,255);
      ledcWrite(3,255);
      rval = 255;
      gval = 255;
      bval = 255;
      sprintf(reply,"%s;OK",seq_id);
    }
  }
  else if (strcmp(command,"OFF") == 0) {
    #ifdef DEBUG
    Serial.println("Command OFF");
    #endif
    if (rval == 0 && gval == 0 && bval == 0){
        sprintf(reply,"%s;NOOP",seq_id);
    }
    else {
      ledcWrite(1,0);
      ledcWrite(2,0);
      ledcWrite(3,0);
      rval = 0;
      gval = 0;
      bval = 0;
      sprintf(reply,"%s;OK",seq_id);
    }
  }
  else if (strcmp(command,"RGB") == 0){
    #ifdef DEBUG
    Serial.println("Command RGB");
    Serial.println(command_param);
    #endif
    char *rgb;
    int old_rval, old_gval, old_bval;
    old_rval = rval;
    old_gval = gval;
    old_bval = bval;
    /*rgb = strtok(command_param,",");*/
    /*rgb = strtok(NULL,"=");*/
    rval = atoi(strtok(command_param,","));
    gval = atoi(strtok(NULL,","));
    bval = atoi(strtok(NULL,","));
    if(old_rval == rval && old_gval == gval && old_bval == bval){
      sprintf(reply,"%s;NOOP",seq_id);
    }
    else{
      ledcWrite(1,rval);
      ledcWrite(2,gval);
      ledcWrite(3,bval);
      sprintf(reply,"%s;OK",seq_id);
    }
  }
  else {
    #ifdef DEBUG
    Serial.println("Topic known, command uknown");
    #endif
    sprintf(reply,"%s;ERROR",seq_id);
 }
 return reply;
} /* end led_1 response */

// Changes in pump1: Input command and command parameters and message id all from callback function, output: response message
char* pump_1_response(char* command, char* command_param, char* seq_id){
  static char reply[20];
  if (strcmp(command,"ON") == 0) {
    #ifdef DEBUG
    Serial.println("Command ON");
    #endif
    if (digitalRead(pump_1) == HIGH){
        sprintf(reply,"%s;NOOP",seq_id);

    }
    else {
      digitalWrite(pump_1,HIGH);
      sprintf(reply,"%s;OK",seq_id);
    }
  }
  else if (strcmp(command,"OFF") == 0) {
    #ifdef DEBUG
    Serial.println("Command OFF");
    #endif
    if (digitalRead(pump_1) == LOW ){
        sprintf(reply,"%s;NOOP",seq_id);
    }
    else {
      digitalWrite(pump_1,LOW);
      sprintf(reply,"%s;OK",seq_id);

    }
  }
  else {
    #ifdef DEBUG
    Serial.println("Topic known, command uknown");
    #endif
    sprintf(reply,"%s;ERROR",seq_id);
 }
 return reply;
} /* end pump_1 response */

/* Function to set sensor measurement intervals: not included in framework yet 
/*char* sensor_config_interval(char* topic, char* command, char* command_param, char* seq_id, unsigned int &sensor_interval){
  static char reply[20];
  //if (strcmp(command,"interval") == 0) {
    int interval;
    command_param = strtok(command_param,"=");
    interval = atoi(strtok(NULL,"="));    
    if ((interval * 1000) == sensor_interval){
      sprintf(reply,"%s;NOOP",seq_id);
      #ifdef DEBUG
      Serial.print(command);
      Serial.print(" for sensor ");
      topic = strtok(topic,"/");
      topic = strtok(NULL,"/");
      topic = strtok(NULL,"/");
      topic = strtok(NULL,"/");
      Serial.print(topic);
      Serial.print(" unchanged. Same value as before: ");
      Serial.print(interval);
      Serial.println(" seconds");
      #endif
    }
    else{
      sensor_interval = interval * 1000;
      sprintf(reply,"%s;OK",seq_id);
      #ifdef DEBUG
      Serial.print("Changed ");
      Serial.print(command);
      Serial.print(" for sensor ");
      topic = strtok(topic,"/");
      topic = strtok(NULL,"/");
      topic = strtok(NULL,"/");
      topic = strtok(NULL,"/");
      Serial.print(topic);
      Serial.print(" to ");
      Serial.print(interval);
      Serial.println(" seconds");
      #endif

    }
  return reply;
}*/
/* This function is used for crud operation regarding sensor based events. 
All input parameters from callback function: Output: response*/
char* event_crud(char* seq_id, char* command_param, event_proto sensor_events[], char* topic, char* cmd){
  #ifdef DEBUG
  Serial.println("Configurating event by user input");
  #endif
  static char reply[200];
  char* temp;
  char* parameters;
  char eventname[16];
  char eventoperator[3];
  float eventthreshold;
  int eventinterval;
  int eventduration;
  char eventoperation[7];
  char automoperation[25] = "";
  int index, free_space;
  #ifdef DEBUG
  Serial.println(parameters);
  #endif
  /* Split messages into parameters, with error handling */
  temp = strtok(command_param,",");
  if (temp == NULL){
    sprintf(reply,"%s;ERROR",seq_id);
    return reply;
  }
  else{
    snprintf(eventname ,16, "%s",temp );
    #ifdef DEBUG
    Serial.println(temp);
    #endif
  }
  temp =  strtok(NULL,",");
  if (temp == NULL){
    sprintf(reply,"%s;ERROR",seq_id);
    return reply;
  }
  else{
    snprintf(eventoperator ,3, "%s",temp );
    #ifdef DEBUG
    Serial.println(temp);
    #endif
   }
  temp = strtok(NULL,",");
  if (temp == NULL){
    sprintf(reply,"%s;ERROR",seq_id);
    return reply;
  }
  else{
    eventthreshold = atof(temp);    
    #ifdef DEBUG
    Serial.println(temp);
    #endif
  }
  temp = strtok(NULL,",");
  if (temp == 0){
    sprintf(reply,"%s;ERROR",seq_id);
    return reply;
  }
  else{
    eventinterval = atoi(temp); 
    #ifdef DEBUG
    Serial.println(temp);
    #endif

  }
  temp = strtok(NULL,",");
  if (temp == 0){
    sprintf(reply,"%s;ERROR",seq_id);
    return reply;
  }
  else{
    eventduration = atoi(temp); 
    #ifdef DEBUG
    Serial.println(temp);
    #endif

  }
  temp = strtok(NULL,",");
  if (temp == NULL){
    sprintf(reply,"%s;ERROR",seq_id);
    return reply;
  }
  else{
    snprintf(eventoperation ,7, "%s",temp );
    #ifdef DEBUG
    Serial.println(temp);
    #endif

  }
  if (strcmp(cmd,"AUTOMATION") == 0){
    temp = strtok(NULL,",");
    if (temp == NULL){
      sprintf(reply,"%s;ERROR",seq_id);
      return reply;
    }
    else{
      snprintf(automoperation ,25, "%s",temp );
      #ifdef DEBUG
      Serial.println(temp);
      #endif
    }
  }
  /* Which operation: create, read, update, delete
  /* In case of read operation: publish event/automation information if found */
  if (strcmp(eventoperation,"READ")==0){
    index = event_crud_read(eventname, sensor_events);
    if (index == -1){
      sprintf(reply,"%s;ERROR: Event not found",seq_id);
    }
    else{
      if (strcmp(cmd,"AUTOMATION") != 0){
        sprintf(reply,"%s;OK:Name:%s,Operator:%s,Threshold:%.2f,Interval:%d,Duration:%d",seq_id,sensor_events[index].ename, sensor_events[index].eoperator, sensor_events[index].ethreshold,sensor_events[index].einterval,sensor_events[index].eduration);
      }
      else {
        sprintf(reply,"%s;OK:Name:%s,Operator:%s,Threshold:%.2f,Interval:%d,Duration:%d,Autom:%d",seq_id,sensor_events[index].ename, sensor_events[index].eoperator, sensor_events[index].ethreshold,sensor_events[index].einterval,sensor_events[index].eduration,sensor_events[index].automoperation);
      }
    }
  }
  /* In case of create: create event if possible, else update event if found or error */
  else if (strcmp(eventoperation,"CREATE")==0){
    index = event_crud_read(eventname, sensor_events);
    free_space = event_free_space(sensor_events);
    if (index == -1  && free_space != -1){
      event_crud_create(eventname, eventoperator, eventthreshold, eventinterval, eventduration, automoperation, sensor_events, free_space, cmd);
      sprintf(reply,"%s;OK",seq_id);
    }
    else if (free_space != -1){
      sprintf(reply,"%s;OK: Event exists, updating",seq_id);
      event_crud_update(eventoperator, eventthreshold, eventinterval, eventduration, automoperation, sensor_events, index, cmd);
    }
    else {
      sprintf(reply,"%s;ERROR: No free space, delete an existing event",seq_id);      
    }
  }
  /* In case of update: update event if possible, else create event if not found or error */
  else if(strcmp(eventoperation,"UPDATE")==0){
    index = event_crud_read(eventname, sensor_events);
    if (index != -1){
      if(event_crud_update(eventoperator, eventthreshold, eventinterval, eventduration, automoperation, sensor_events, index, cmd)){
        sprintf(reply,"%s;OK",seq_id);
      }
      else{
      sprintf(reply,"%s;NOOP",seq_id);  
      }
    }
    else {
      free_space = event_free_space(sensor_events);
      if (free_space != -1){
        sprintf(reply,"%s;ERROR: Event doesn't exist, creating",seq_id);
        event_crud_create(eventname, eventoperator, eventthreshold, eventinterval, eventduration, automoperation, sensor_events, free_space, cmd);
      }
      else {
        sprintf(reply,"%s;ERROR: Event doens't exist and no free space, delete an existing event",seq_id);      
      } 
    }
  }    
  /* Delete */
  else if(strcmp(eventoperation,"DELETE")==0){
    index = event_crud_read(eventname, sensor_events);
    if (index == -1){
      sprintf(reply,"%s;ERROR: Event doens't exist.",seq_id);      
    }
    else{
      event_crud_delete(index, sensor_events, topic, cmd);
      sprintf(reply,"%s;OK",seq_id);      
    }
  }
  return reply;
} /* end event_crud */

/* This function checks whether there is space for a new event */
int event_free_space(event_proto sensor_events[]){
  int result = -1;
  for(int i=0; i<NUMBER_OF_EVENTS; i++){
    if(strcmp(sensor_events[i].ename,"") == 0){
      result = i;     
    }
  }
  return result;
}

int event_crud_read(char* eventname, event_proto sensor_events[]){
  int result = -1;
  for(int i=0; i<NUMBER_OF_EVENTS; i++){
    if(strcmp(sensor_events[i].ename,eventname) == 0){
      #ifdef DEBUG
      Serial.println("Event with same name found");
      #endif
      result = i;     
    }
  }
  return result;
}

void event_crud_create(char* eventname, char* eventoperator, float eventthreshold, int eventinterval, int eventduration, char* automoperation, event_proto sensor_events[], int free_space, char* cmd){
  snprintf(sensor_events[free_space].ename,16, "%s", eventname);  
  snprintf(sensor_events[free_space].eoperator,3, "%s", eventoperator);
  sensor_events[free_space].ethreshold = eventthreshold;
  sensor_events[free_space].einterval = eventinterval;
  sensor_events[free_space].eduration = eventduration;
  sensor_events[free_space].eset = true;
  if (strcmp(cmd, "AUTOMATION") == 0){
    snprintf(sensor_events[free_space].automoperation,25, "%s", automoperation);
  }
}

bool event_crud_update(char* eventoperator, float eventthreshold, int eventinterval, int eventduration, char* automoperation, event_proto sensor_events[], int index, char* cmd){
  bool result;
  if(strcmp(eventoperator,sensor_events[index].eoperator) == 0 && eventthreshold == sensor_events[index].ethreshold && eventinterval == sensor_events[index].einterval && eventduration == sensor_events[index].eduration){
    result = false; 
  }
  else{
    snprintf(sensor_events[index].eoperator,3, "%s", eventoperator);
    sensor_events[index].ethreshold = eventthreshold;
    sensor_events[index].einterval = eventinterval;
    sensor_events[index].eduration = eventduration;
    sensor_events[index].eset = true;
    if (strcmp(cmd, "AUTOMATION") == 0){
      snprintf(sensor_events[index].automoperation,25, "%s", automoperation);
    }
    result = true;
  }
  return result;
}

void event_crud_delete(int index, event_proto sensor_events[],char* topic, char* cmd){
  snprintf(sensor_events[index].ename,16, "");  
  snprintf(sensor_events[index].eoperator,3, "");
  sensor_events[index].ethreshold = 0;
  sensor_events[index].einterval = 0;
  sensor_events[index].eduration = 0;
  sensor_events[index].eset = false;
  active_events_num -= 1;
  if (strcmp(cmd, "AUTOMATION") == 0){
    autom_reset(sensor_events,index);
    snprintf(sensor_events[index].automoperation,25, "%s", "");
  }
  /* Publish empty message to alarm topic: needed to turn event window green/ok and empty */
  client.publish(topic,"");
}

/* This function publishes the MQTT reponse from any given function */
void publish_response(char* topic,char* message){
  #ifdef DEBUG
  Serial.println(message);
  #endif
  client.publish(topic,message);
}

/* This function is used to check the pump at each loop and turn it off */
void check_pump(){
  if (digitalRead(pump_1) == HIGH){
    delay(pumping_time);
    digitalWrite(pump_1,LOW);
  }
}

/* This function is used to publish all measurements. Intervals can be changed by hand at the top, */
void publish_measurements(){
unsigned long now = millis();
  if((now - bright_last) >= bright_interv){
    out_brightness_1();
  }
  if((now - temp_last) >= temp_interv){
    out_temp_1();
  }
  if((now - humidity_last) >= humidity_interv){
    out_humidity_1();
  }
  if((now - pressure_last) >= pressure_interv){
    out_pressure_1();
  }
  if((now - moisture_last) >= moisture_interv){
    out_moisture_1();
  }
  if((now - rain_last) >= rain_interv){
    out_rain_1();
  }
  //delay(250), was necessary to ensure that messages are really sent of in case board was sent to sleep after. now done in loop;
}

/* This function is used to check, update, and fire events during every loop. Input is sensor specific: the measurement value
as well as the associated event-struct array and the topic for notifications*/
void check_events(event_proto sensor_events[],float measurement_value, char* topic){
  int i;
  for(i=0;i<NUMBER_OF_EVENTS;i++){ 
    bool event_condition_check = false; /* state: is event condition met in this loop? set to false first*/
    if (sensor_events[i].etriggered &&  sensor_events[i].eset){ 
      /* if event is set and triggered */
      if((sensor_events[i].eduration * 1000) > (millis()-sensor_events[i].estart)){ 
        /* if the duration is not over */
        if((sensor_events[i].einterval * 1000) < (millis()-sensor_events[i].elastnotification)){ 
          /* if the interval between messages is over 
             check meaurement value to see ifevent condition is met*/
          event_condition_check = check_event_condition(measurement_value, sensor_events[i].eoperator, sensor_events[i].ethreshold);
          if(event_condition_check){ /* is the event condition true? */
            //notify, automation?, update 
            event_notify(sensor_events,i,topic,measurement_value);
            autom_action(sensor_events,i); 
            event_update(sensor_events,i); 
            }
          else{//reset event
            #ifdef DEBUG
            Serial.println("Resetting event: condition not met");
            #endif
            event_reset(sensor_events,i,topic);
          }
        }
        else{
          #ifdef DEBUG
          Serial.println("Notification Interval not over, waiting");
          #endif
          continue;
        }
      } 
      else if((sensor_events[i].eduration * 1000) <= (millis()-sensor_events[i].estart)){
        #ifdef DEBUG
        Serial.println("Resetting event: duration is over");
        #endif
        event_reset(sensor_events,i,topic);
      }
    }
    //event not yet triggered
    else if(sensor_events[i].eset && !sensor_events[i].etriggered){
      event_condition_check = check_event_condition(measurement_value, sensor_events[i].eoperator, sensor_events[i].ethreshold);
      if(event_condition_check){
        //notify 
        event_notify(sensor_events,i,topic,measurement_value); 
        event_update(sensor_events,i);
        autom_action(sensor_events,i); 
      }
    }
  } /* end for */
} /* end event_check */

/* This function checks whether an event condition is met and outputs bool */
bool check_event_condition(float value, char* comp_operator, float threshold){
  bool result = false;
  #ifdef DEBUG
  Serial.print("Checking if Event condition is met: ");
  Serial.print(value);
  Serial.print(comp_operator);
  Serial.println(threshold);
  #endif
  if(strcmp("<",comp_operator) == 0){
    result = value < threshold;
  }
  else if(strcmp("<=",comp_operator) == 0){
    result = value <= threshold;
  }  
  else if(strcmp("==",comp_operator) == 0){
    result = value == threshold;
  }  
  else if(strcmp(">=",comp_operator) == 0){
    result = value >= threshold;
  }  
  else if(strcmp(">",comp_operator) == 0){
    result = value > threshold;
  }
  return result;
} /* end check event condition */

/* This function notifies the client */
void event_notify(event_proto sensor_events[], int i, char* topic, float measurement_value){
  #ifdef DEBUG
  Serial.println("Notifying MQTT Bridge");
  #endif
  char message[200];
  if (strcmp(sensor_events[i].automoperation, "") != 0){
    sprintf(message,"Event: %s. %.2f %s %.2f. %s",sensor_events[i].ename, measurement_value, sensor_events[i].eoperator, sensor_events[i].ethreshold, sensor_events[i].automoperation);
    client.publish(topic,message); 
  }
  else{
    sprintf(message,"Event: %s. %.2f %s %.2f",sensor_events[i].ename, measurement_value, sensor_events[i].eoperator, sensor_events[i].ethreshold);
    client.publish(topic,message);
  }
}
/* This function resets and event (i.e. untriggers it, if duration is over or condition is no longer met */
void event_reset(event_proto sensor_events[], int i, char* topic){
  #ifdef DEBUG
  Serial.println("Resetting event. No longer active or duration is over");
  #endif
  active_events_num -=  1;
  sensor_events[i].etriggered = false;
  sensor_events[i].estart = 0;
  sensor_events[i].elastnotification = 0;
  if(strcmp(sensor_events[i].automoperation,"") != 0){
    autom_reset(sensor_events,i);
  }
  client.publish(topic,"");
}

/* This function updates counters to observe event message interval and duration */
void event_update(event_proto sensor_events[], int i){
  #ifdef DEBUG
  Serial.println("Updating event. Setting as active or updating times");
  #endif
  //Serial.print("Event activated? ");
  //Serial.println(sensor_events[i].etriggered);
  if (sensor_events[i].etriggered == false){
    sensor_events[i].etriggered = true;
    sensor_events[i].estart = millis();
    active_events_num += 1;
  }
  //Serial.println("Updating Last notification Event");
  sensor_events[i].elastnotification = millis();
  //Serial.println( sensor_events[i].elastnotification );
}

/* This function enacts automations */
void autom_action(event_proto sensor_events[], int i){
  char parameter[20];
  char tmp[25];
  char* tmp2;
  Serial.println("Automation triggering actuator");
  Serial.println(sensor_events[i].automoperation);
  if (strcmp("funcLed_1On",sensor_events[i].automoperation)==0){
    ledcWrite(1,255);
    ledcWrite(2,255);
    ledcWrite(3,255);
    rval = 255;
    gval = 255;
    bval = 255;
  }
  else if (strcmp("funcLed_1Off",sensor_events[i].automoperation)==0){
    ledcWrite(1,0);
    ledcWrite(2,0);
    ledcWrite(3,0);
    rval = 0;
    gval = 0;
    bval = 0;    
  }
  else if (strcmp("funcPump_1On",sensor_events[i].automoperation)==0){
    digitalWrite(pump_1,HIGH);
  }
  else if (strcmp("funcPump_1Off",sensor_events[i].automoperation)==0){
    digitalWrite(pump_1,LOW);
 }
  else if (strstr(sensor_events[i].automoperation,"funcLed_1Rgb")!= NULL){
    snprintf(tmp,25,"%s",sensor_events[i].automoperation);
    Serial.println(tmp);
    tmp2 = strtok(tmp,":");
    rval = atoi(strtok(NULL,":"));
    gval = atoi(strtok(NULL,":"));
    bval = atoi(strtok(NULL,":"));
    ledcWrite(1,rval);
    ledcWrite(2,gval);
    ledcWrite(3,bval);   
  }
  return;
}

/* This function resets all actuators after and automation has ended (i.e. turns them off) */
void autom_reset(event_proto sensor_events[], int i){
  Serial.println("Resetting automation actuator");
  Serial.println(sensor_events[i].automoperation);
  if (strstr(sensor_events[i].automoperation,"Pump_1")!= NULL){
    if(digitalRead(pump_1)==HIGH){
      digitalWrite(pump_1,LOW);
    }
  }
  else if (strstr(sensor_events[i].automoperation,"Led_1")!= NULL){
    ledcWrite(1,0);
    ledcWrite(2,0);
    ledcWrite(3,0);
    rval = 0;
    gval = 0;
    bval = 0;   
  }
  return;
}


/* This function is used to send the board to sleep */
void to_sleep(){
  #ifdef DEBUG
  Serial.println("Disconnecting MQTT and WIFI. Going to sleep using timer.");
  #endif
  #ifdef CRUD_SLEEP
  device_configuration("delete");
  if(checkout_successful == true) {
    Serial.println("Checkout successful, going to sleep");
    checkout_successful = false;
  }
  else{
    Serial.println("Checkout unsuccessful, sent error to mqtt, going to sleep anyways");
    client.publish(ERROR_P,UUID"; Error deleting configuration");
  }
  #endif
  client.disconnect();
  WiFi.disconnect();
  while(client.connected() || WiFi.status() != WL_CONNECTED ) {
    delay(10);
  }
    esp_bluedroid_disable();
    esp_bt_controller_disable();
    esp_wifi_stop();
    esp_deep_sleep_start();
}
/* END OF SETUP */

/* START OF LOOP */
void loop() {
  if (!client.connected()) {
    #ifdef DEBUG
    Serial.println("Lost MQTT-connection. Reconnecting");
    #endif
    if( WiFi.status() != WL_CONNECTED){
      #ifdef DEBUG
      Serial.println("Lost Wifi-Connection as well. Reconnecting");
      #endif
      setup_wifi();
    } 
    setup_mqtt();
  }
  publish_measurements();
  delay(500); /* need to wait for messages to be sent off (if board is sent to sleep, sometimes messages are lost) */ 
  client.loop();
 
  check_events(moisture1_events,moisture,MOIST1_TOPIC_EVENT);
  check_events(temperature1_events,temp,TEMP1_TOPIC_EVENT);
  check_pump();
  //if (active_events_num == 0){
  #ifdef SLEEP_CYCLE
  to_sleep();
  #endif
  //}  
}
