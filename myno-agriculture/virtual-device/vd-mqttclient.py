import time
import traceback

import paho.mqtt.client as mqtt
import logging
import aggregat
import aggregatPreload
import calculation
import time
from pathlib import Path

PATH_VD = 'time_vd.txt'

BROKER_ADDR = "localhost"
#BROKER_ADDR = "192.168.0.110"
BROKER_PORT = 1883

CREATE_TOPIC = 'yang/config/create'
CREATE_RESPONSE_TOPIC = 'yang/config/create/response/'
RETRIEVE_TOPIC = 'yang/config/retrieve'
RETRIEVE_RESPONSE_TOPIC = 'yang/config/retrieve/response/'
UPDATE_TOPIC = 'yang/config/update'
UPDATE_RESPONSE_TOPIC = 'yang/config/update/response/'
DELETE_TOPIC = 'yang/config/delete'
DELETE_RESPONSE_TOPIC = 'yang/config/delete/response/'
RESPONSE_TOPIC = "response/"

VIRTUAL_DEVICE_UUID = "199A-4F4F-8F69-6B8F3C2E78ED"

NC_DEBUG = True
PRELOAD_FLAG = True

logger = logging.getLogger("virtual-device")

uuid_set = set()
topics_set = set()
sensor_topics_set = set()
conf_topics_set = set()
event_topics_set = set()
auto_topics_set = set()

counter_set = set()
counter_dict = {}
sensor_dict = {}

###  MQTT functions
def mqtt_connect(mqtt_client, userdata, flags, rc):
    logger.info("Connected to broker with result code " + str(rc))
    mqtt_client.subscribe("yang/config/#")
    mqtt_client.subscribe("response/#")


def mqtt_message(mqtt_client, userdata, msg):
    global ontology, vd_ontology
    global uuid_set, topics_set, sensor_topics_set, conf_topics_set, event_topics_set, auto_topics_set
    #global device_category
    parameter = ""

    logger.debug(msg.topic + " " + msg.payload.decode())
    a = (msg.topic.split("/"))

    if msg.topic == CREATE_TOPIC or msg.topic == 'yang/config':
        rawmsg = msg.payload.decode().split(";")
        uuid = rawmsg[0]
        conf = rawmsg[1]

        #rawmsg may be splitted in chunks, wait until END
        if conf != "END":
            ontology = conf

        print("MQTT Payload: " + ontology)

        if uuid != VIRTUAL_DEVICE_UUID and conf == "END":
        # proceed device description aggregation
            start = time.time()
            start_timestamp = time.strftime("%H:%M:%S")
            if(PRELOAD_FLAG):
                uuid, topics_set1, sensor_topics_set1, conf_topics_set1, event_topics_set1, auto_topics_set1, vd_ontology = aggregatPreload.process_description(uuid, ontology)
                uuid_set.add(uuid)
                topics_set |= topics_set1
                sensor_topics_set |= sensor_topics_set1
                conf_topics_set |= conf_topics_set1
                event_topics_set |= event_topics_set1
                auto_topics_set |= auto_topics_set1


                for topic in topics_set1:
                    try:
                        mqttTopic = topic + VIRTUAL_DEVICE_UUID
                        mqtt_client.subscribe(mqttTopic)
                        print('mqtt client subscribe to ' + mqttTopic)
                        respTopic = RESPONSE_TOPIC + uuid
                        mqtt_client.subscribe(respTopic)
                        print('mqtt client subscribe to ' + respTopic)
                    except Exception as err:
                        track = traceback.format_exc()
                        print(track)

                for topic in conf_topics_set1:
                    try:
                        mqttTopic = topic + VIRTUAL_DEVICE_UUID
                        mqtt_client.subscribe(mqttTopic)
                        print('mqtt client subscribe to ' + mqttTopic)
                        respTopic = RESPONSE_TOPIC + uuid
                        mqtt_client.subscribe(respTopic)
                        print('mqtt client subscribe to ' + respTopic)
                    except Exception as err:
                        track = traceback.format_exc()
                        print(track)

                for topic in auto_topics_set1:
                    try:
                        mqttTopic = topic + VIRTUAL_DEVICE_UUID
                        mqtt_client.subscribe(mqttTopic)
                        print('mqtt client subscribe to ' + mqttTopic)
                        respTopic = RESPONSE_TOPIC + uuid
                        mqtt_client.subscribe(respTopic)
                        print('mqtt client subscribe to ' + respTopic)
                    except Exception as err:
                        track = traceback.format_exc()
                        print(track)

                for topic in sensor_topics_set1:
                    try:
                        sensorTopic = topic + uuid
                        mqtt_client.subscribe(sensorTopic)
                        print('mqtt client subscribe to ' + sensorTopic)
                    except Exception as err:
                        track = traceback.format_exc()
                        print(track)

                for topic in event_topics_set1:
                    try:
                        sensorTopic = topic + uuid
                        mqtt_client.subscribe(sensorTopic)
                        print('mqtt client subscribe to ' + sensorTopic)
                    except Exception as err:
                        track = traceback.format_exc()
                        print(track)

                end = time.time()
                total = end - start
                printTime(start_timestamp, total, PATH_VD, uuid + ',' + "create")

            else:
                vd_ontology = aggregat.process_description(ontology)
            #print("VD ontology" + vd_ontology)
            mqtt_client.publish(CREATE_TOPIC, (VIRTUAL_DEVICE_UUID + ";" + vd_ontology))
            mqtt_client.publish(CREATE_TOPIC, (VIRTUAL_DEVICE_UUID + ";END"))
            print("END detected")

    elif a[0] == "response" and a[1] != VIRTUAL_DEVICE_UUID:
        # response collect
        raw = msg.payload.decode().split(';')
        if(raw[0] in counter_set):
            temp = counter_dict[raw[0]]
            if(temp):
                counter_dict[raw[0]] = temp + ", " + a[1] + "=" + raw[1]
            else:
                counter_dict[raw[0]] = a[1] + " = " + raw[1]
            mqtt_client.publish(RESPONSE_TOPIC + VIRTUAL_DEVICE_UUID, (raw[0] + ";" + counter_dict[raw[0]]))

    elif a[0] == "sensor" and a[1] != VIRTUAL_DEVICE_UUID:
        # sensor values collect
        sensorTopic = str(a[0] + "/" + a[1] + "/" + a[2] + "/" )
        print('sensor topic: ' + sensorTopic)
        if(sensorTopic in sensor_topics_set):
            # aggregate sensor values and publish to VD topic
            if(sensorTopic not in sensor_dict):
                sensor_dict[sensorTopic] = calculation.SensorAggregat(sensorTopic)
            result = sensor_dict[sensorTopic].getAvg(msg.payload.decode())
            print("avg: " + str(result))
            mqtt_client.publish(sensorTopic + VIRTUAL_DEVICE_UUID, result)

    elif a[0] == 'event' and a[1] != VIRTUAL_DEVICE_UUID:
        #event/sensor/moisture/moisture_1/%s
        eventTopic = str(a[0] + "/" + a[1] + "/" + a[2] + "/" + a[3] + "/")
        print('sensor topic: ' + eventTopic)
        mqtt_client.publish(eventTopic + VIRTUAL_DEVICE_UUID, msg.payload.decode())

    elif a[0] == "actuator" or a[0] == "config" or a[0] == "automation":
        # actuator spread
        rawmsg = msg.payload.decode().split(";")
        if (msg.topic):
            print('actuator topic: ' + msg.topic)

        if(a[len(a)-1] == VIRTUAL_DEVICE_UUID):
            vd_uuid = a[len(a)-1]

            counter = rawmsg[0]
            counter_set.add(counter)
            counter_dict[counter] = ""
            print("counter: " + counter)

            mqttMethod = rawmsg[1]
            print("mqttMethod: " + mqttMethod)

            if(len(rawmsg)>2):
                parameter = rawmsg[2] #extract parameter
                print("parameter: " + parameter)

            # if actuator topic, then publish to all devices: actuator/pump/pump_1/%s
            topic = str(msg.topic).rstrip(vd_uuid)
            if(parameter):
                msg = counter + ";" + mqttMethod + ";" + parameter
            else:
                msg = counter + ";" + mqttMethod
            for uuid in uuid_set:
                try:
                    mqttTopic = topic + uuid
                    mqtt_client.publish(mqttTopic, msg)
                    print('mqtt client publish to ' + mqttTopic + " " + msg)
                except Exception as err:
                    track = traceback.format_exc()
                    print(track)
        time.sleep(0.2)  # wait for response


def printTime(start, zeit, path, note):
    logger.debug(zeit)
    #path = 'yang\time_rdflib.txt'
    my_file = Path(path)
    try:
        if my_file.is_file():
            logger.debug("file exists")
            daten = open(path, mode='a')
        else:
            logger.debug("file doe not exists")
            daten = open(path, mode='x')

        timestamp = time.strftime("%H:%M:%S")
        daten.write(str(start) + ',' + str(timestamp) + "," + str(zeit) + "," + str(note) + '\n')
        daten.close()
    except Exception as err:
        logger.error('Behandle Laufzeitfehler: %s', "major", exc_info=1)

### ENTRY POINT
if __name__ == "__main__":
    if NC_DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = mqtt_connect
    mqtt_client.on_message = mqtt_message

    ### Run....
    mqtt_client.connect(BROKER_ADDR, BROKER_PORT, 60)

    #mqtt_client.loop_forever()
    mqtt_client.loop_start()

    logger.info("init complete, starting main loop")


    running = True
    while running:
         try:
             time.sleep(10)
         except KeyboardInterrupt:
             logger.info("got keyboard interrupt")
             running = False

    logger.info("Shutting down!")
