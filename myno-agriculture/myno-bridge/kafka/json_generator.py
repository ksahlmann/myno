import json
import traceback
import paho.mqtt.client as mqtt
import logging

from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugin import register, Parser
register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')

logger = logging.getLogger("json-generator")
NC_DEBUG = False

BROKER_ADDR = "localhost"
BROKER_PORT = 1883
KAFKA_TOPIC = "kafka/config"

base = "http://yang-netconf-mqtt#"
initNs = {"rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#", "base":"http://yang-netconf-mqtt#", "onem2m":"http://www.onem2m.org/ontology/Base_Ontology/base_ontology#", "om-2":"http://www.ontology-of-units-of-measure.org/resource/om-2/"}

def generate_json_kafka(json_str):
    print("parseDevicesJson")

    raw_data = {}

    g = Graph()
    g.parse(data=json_str, format="json-ld", base="http://yang-netconf-mqtt#")

    # q = prepareQuery(
    #     'SELECT DISTINCT ?device ?properties ?functions ?mqttTopic  WHERE {?device rdf:type onem2m:Device . ?device onem2m:hasThingProperty ?properties .  ?device onem2m:hasFunctionality ?functions .  ?functions rdf:type onem2m:MeasuringFunctionality .  '
    #     '?services onem2m:exposesFunctionality ?functions . ?services onem2m:hasOutputDataPoint ?outDp . ?outDp  base:mqttTopic ?mqttTopic . } ', initNs)
    # result = g.query(q)
    #
    # for row in result:
    #     print(" %s %s %s %s" % row)
        #str(row["device"])


    # only device properties
    q = prepareQuery(
        'SELECT DISTINCT ?device ?properties ?value WHERE {?device rdf:type onem2m:Device . ?device onem2m:hasThingProperty ?properties .  ?properties onem2m:hasValue ?value . }', initNs)
    result = g.query(q)
    for row in result:
        logger.debug(" %s %s %s" % row)
        if(str(row["properties"]) == base + "deviceUuid"):
            logger.debug(str(row["properties"]))
            raw_data["device-uuid"] = str(row["value"])

    # TODO add location
    raw_data["location"] = "building4/room2.02"

    # only functions and mqtt topics
    q = prepareQuery(
        'SELECT DISTINCT ?functions ?mqttTopic ?units WHERE {?functions rdf:type onem2m:MeasuringFunctionality .  ?services onem2m:exposesFunctionality ?functions . ?services onem2m:hasOutputDataPoint ?outDp . ?outDp  base:mqttTopic ?mqttTopic . ?outDp om-2:hasUnit ?units .} ', initNs)
    #'SELECT DISTINCT ?functions ?mqttTopic ?units WHERE {?functions rdf:type onem2m:MeasuringFunctionality .  ?services onem2m:exposesFunctionality ?functions . ?services onem2m:hasOutputDataPoint ?outDp . ?outDp  base:mqttTopic ?mqttTopic . ?functions om-2:hasUnit ?units .} ', initNs)
    result = g.query(q)

    sensors_list = []
    for row in result:
        logger.debug(" %s %s %s" % row)
        sens_dict = {}
        sens_dict["mqtt-topic"] = str(row["mqttTopic"])
        sens_dict["units"] = str(row["units"]).split("/om-2/")[1]

        sensors_list.append(sens_dict)

    raw_data["sensors"] = sensors_list

    logger.debug(raw_data)
    build_json(raw_data)


def build_json(raw_data):

    kafka_json = json.dumps(raw_data)
    logger.debug(kafka_json)

    mqtt_client = mqtt.Client()
    #mqtt_client.on_connect = mqtt_connect
    #mqtt_client.on_message = mqtt_message

    mqtt_client.connect(BROKER_ADDR, BROKER_PORT, 60)

    mqtt_client.publish(KAFKA_TOPIC, kafka_json)

    mqtt_client.disconnect()

    #mqtt_client.loop_start()



if __name__ == "__main__":

    if NC_DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    ONTOLOGY_FILE_5 = "../ontology/bright_temp_moist_motion_led.owl"
    DEVICE_UUID_5 = "SIMULATOR5-3A78-4F4F-8F69-6B8F3C2E78DD"
    with open(ONTOLOGY_FILE_5) as data_file:
        ontology = (data_file.read() % (DEVICE_UUID_5, DEVICE_UUID_5, DEVICE_UUID_5, DEVICE_UUID_5, DEVICE_UUID_5))
        #print(ontology)
        try:
            generate_json_kafka(ontology)
        except Exception as err:
            track = traceback.format_exc()
            print(track)
