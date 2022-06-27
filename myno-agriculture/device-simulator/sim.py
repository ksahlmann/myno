import time
import random
import threading
import paho.mqtt.client as mqtt


threadLock = threading.Lock()
DEVICE_UUID_1 = "SIMULATOR1-8A12-4F4F-8F69-6B8F3C2E78DD"
DEVICE_UUID_2 = "SIMULATOR2-5A68-4F4F-8F69-6B8F3C2E78DD"
DEVICE_UUID_3 = "SIMULATOR3-9A29-4F4F-8F69-6B8F3C2E78DD"
DEVICE_UUID_4 = "SIMULATOR4-7A56-4F4F-8F69-6B8F3C2E78DD"
DEVICE_UUID_5 = "SIMULATOR5-3A78-4F4F-8F69-6B8F3C2E78DD"
DEVICE_UUID_6 = "SIMULATOR6-1A45-4F4F-8F69-6B8F3C2E78DD"
DEVICE_UUID_7 = "SIMULATOR7-1A45-4F4F-8F69-6B8F3C2E78DD"
DEVICE_UUID_8 = "SIMULATOR8-1A45-4F4F-8F69-6B8F3C2E78DD"

BROKER_ADDR = "localhost"
BROKER_PORT = 1883

ONTOLOGY_FILE_1 = "ontology_with_token.owl"
ONTOLOGY_FILE_2 = "relay_moist_temp.owl"
ONTOLOGY_FILE_3 = "brightness_led_smoke.owl"
ONTOLOGY_FILE_4 = "bright_motion_led.owl"
ONTOLOGY_FILE_5 = "bright_temp_moist_motion_led.owl"
ONTOLOGY_FILE_6 = "bright_motion_led-rgb.owl"
ONTOLOGY_FILE_7 = "MYNO-Update-new-opt.owl"
#ONTOLOGY_FILE_7 = "MYNO-Update-new.owl"
#ONTOLOGY_FILE_8 = "prototype_units-events.owl"
ONTOLOGY_FILE_8 = "prototype_units-events-opt.owl"


LEGACY_TOPIC = 'yang/config'
CREATE_TOPIC = 'yang/config/create'
RETRIEVE_TOPIC = 'yang/config/retrieve'
DELETE_TOPIC = 'yang/config/delete'
UPDATE_TOPIC = 'yang/config/update'

CMD_TOPIC = 'led/' + DEVICE_UUID_1

SENSOR_TOPIC_1 = 'sensor/temperature/temperature_1/' + DEVICE_UUID_8

RESPONSE_TOPIC = 'response/' + DEVICE_UUID_1

STATE = "OFF"

def mqtt_connect(mqtt_client, userdata, flags, rc):
    mqtt_client.subscribe("led/" + DEVICE_UUID_1)

    mqtt_client.subscribe("yang/config/#")

    #mqtt_client.subscribe(CREATE_TOPIC + "/response/#")
    #mqtt_client.subscribe(RETRIEVE_TOPIC + "/response/#")
    #mqtt_client.subscribe(UPDATE_TOPIC + "/response/#")
    #mqtt_client.subscribe(DELETE_TOPIC + "/response/#")


def mqtt_message(mqtt_client, userdata, msg):
    print("MESSAGE topic: " + msg.topic + "MESSAGE payload: " + msg.payload.decode())
    global STATE
    a = (msg.topic.split("/"))
    if a[2] == "retrieve" and a[3] == 'response':  # yang/config/read/response/UUID
        print("retrieve response " +  a[4] + "MESSAGE payload: " + msg.payload.decode())
    elif a[2] == "delete" and a[3] == 'response':  # yang/config/delete/response/UUID
        print("delete response " +  a[4] + "MESSAGE payload: " + msg.payload.decode())
    elif a[2] == "create" and a[3] == 'response':  # yang/config/create/response/UUID
        print("create response " +  a[4] + "MESSAGE payload: " + msg.payload.decode())
    elif a[2] == "update" and a[3] == 'response':  # yang/config/update/response/UUID
        print("update response " +  a[4] + "MESSAGE payload: " + msg.payload.decode())

    else:
        rawcmd = msg.payload.decode().split(';')
        seq_id = rawcmd[0]
        cmd = rawcmd[1]

        if cmd == 'color':
            if len(rawcmd) >=3:
                param = rawcmd[2].split('=')
                if len(param) >=2:
                    cmd = rawcmd[2].split('=')[1]

        if cmd == STATE:
            print("CTRL RECEIVED, ALREADY IN STATE: "+cmd)
            mqtt_client.publish(RESPONSE_TOPIC, seq_id+";NOOP")
        elif cmd in {"ON", "OFF", "GREEN", 'orange', 'all', 'yellow', 'green', 'red'}:
            print("CTRL RECEIVED, STATE SWITCH: "+STATE+" -> "+cmd)
            STATE = cmd
            mqtt_client.publish(RESPONSE_TOPIC, seq_id+";OK")
        else:
            print("CTRL RECEIVED, UNKNOWN CTRL")
            mqtt_client.publish(RESPONSE_TOPIC, seq_id+";ERROR")

def sensor_loop():
    while True:
        mqtt_client.publish(SENSOR_TOPIC_1, random.randint(0, 1000))
        time.sleep(5)


if __name__ == "__main__":
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = mqtt_connect
    mqtt_client.on_message = mqtt_message

    mqtt_client.connect(BROKER_ADDR, BROKER_PORT, 60)

    #first read
#    mqtt_client.publish(RETRIEVE_TOPIC, DEVICE_UUID_1)

    # add devices
    # device 1
    # with open(ONTOLOGY_FILE_1) as data_file:
    #     ontology = DEVICE_UUID_1 + ";" + (data_file.read() % (DEVICE_UUID_1, SENSOR_TOPIC_1))
    #     mqtt_client.publish(CREATE_TOPIC, ontology)
    #     mqtt_client.publish(CREATE_TOPIC, DEVICE_UUID_1 + ";END")
    #     print("Ontology 1 published")
    # device 2
    # with open(ONTOLOGY_FILE_2) as data_file:
    #     ontology = DEVICE_UUID_2 + ";" + (data_file.read() % (DEVICE_UUID_2, DEVICE_UUID_2, DEVICE_UUID_2))
    #     mqtt_client.publish(CONFIG_TOPIC, ontology)
    #     mqtt_client.publish(CONFIG_TOPIC, DEVICE_UUID_2 + ";END")
    #     print("Ontology 2 published")
    # device 3
    # with open(ONTOLOGY_FILE_3) as data_file:
    #     ontology = DEVICE_UUID_3 + ";" + (data_file.read() % (DEVICE_UUID_3, DEVICE_UUID_3, DEVICE_UUID_3))
    #     mqtt_client.publish(CONFIG_TOPIC, ontology)
    #     mqtt_client.publish(CONFIG_TOPIC, DEVICE_UUID_3 + ";END")
    #     print("Ontology 3 published")

    # device 4
    # with open(ONTOLOGY_FILE_4) as data_file:
    #     ontology = DEVICE_UUID_4 + ";" + (data_file.read() % (DEVICE_UUID_4, DEVICE_UUID_4, DEVICE_UUID_4))
    #     mqtt_client.publish(CREATE_TOPIC, ontology)
    #     mqtt_client.publish(CREATE_TOPIC, DEVICE_UUID_4 + ";END")
    #     print("Ontology 4 published")

    # device 5
    # with open(ONTOLOGY_FILE_5) as data_file:
    #     #     ontology = DEVICE_UUID_5 + ";" + (data_file.read() % (DEVICE_UUID_5, DEVICE_UUID_5, DEVICE_UUID_5, DEVICE_UUID_5, DEVICE_UUID_5))
    #     #     mqtt_client.publish(CREATE_TOPIC, ontology)
    #     #     mqtt_client.publish(CREATE_TOPIC, DEVICE_UUID_5 + ";END")
    #     #     print("Ontology 5 published")

    #device 6
    # with open(ONTOLOGY_FILE_6) as data_file:
    #     ontology = DEVICE_UUID_6 + ";" + (data_file.read() % (DEVICE_UUID_6, DEVICE_UUID_6, DEVICE_UUID_6))
    #     mqtt_client.publish(CREATE_TOPIC, ontology)
    #     mqtt_client.publish(CREATE_TOPIC, DEVICE_UUID_6 + ";END")
    #     print("Ontology 6 published")

    #device 7
    with open(ONTOLOGY_FILE_7) as data_file:
         ontology = DEVICE_UUID_7 + ";" + (data_file.read() % (DEVICE_UUID_7, DEVICE_UUID_7, DEVICE_UUID_7))
         mqtt_client.publish(LEGACY_TOPIC, ontology)
         mqtt_client.publish(LEGACY_TOPIC, DEVICE_UUID_7 + ";END")
         print("Ontology 7 published")

    #device 8
    with open(ONTOLOGY_FILE_8) as data_file:
        ontology = DEVICE_UUID_8 + ";" + (data_file.read().replace('%s', DEVICE_UUID_8) )
        #ontology = DEVICE_UUID_8 + ";" + data_file.read()
        mqtt_client.publish(CREATE_TOPIC, ontology)
        mqtt_client.publish(CREATE_TOPIC, DEVICE_UUID_8 + ";END")
        print("Ontology 8 published")

    # read devices from Netconf
    # mqtt_client.publish(RETRIEVE_TOPIC, DEVICE_UUID_1)
    # mqtt_client.publish(RETRIEVE_TOPIC, DEVICE_UUID_2)
    # mqtt_client.publish(RETRIEVE_TOPIC, DEVICE_UUID_3)
    # #mqtt_client.publish(RETRIEVE_TOPIC, DEVICE_UUID_4)
    # mqtt_client.publish(RETRIEVE_TOPIC, DEVICE_UUID_5)
    # mqtt_client.publish(RETRIEVE_TOPIC, DEVICE_UUID_6)
    # mqtt_client.publish(RETRIEVE_TOPIC, 'SIMULATOR6-9A29-4F4F-8F69-6B8F3C2E78DD')

    time.sleep(5)
    #update device 8
    # with open(ONTOLOGY_FILE_8) as data_file:
    #     ontology = DEVICE_UUID_8 + ";" + (data_file.read().replace('%s', DEVICE_UUID_8) )
    #     #ontology = DEVICE_UUID_5 + ";" + (data_file.read() % (DEVICE_UUID_5, DEVICE_UUID_5, DEVICE_UUID_5))
    #     mqtt_client.publish(UPDATE_TOPIC, ontology)
    #     mqtt_client.publish(UPDATE_TOPIC, DEVICE_UUID_8 + ";END")
    #     print("Device 8 update")

    #time.sleep(20)
    # delete device
    #mqtt_client.publish(DELETE_TOPIC, DEVICE_UUID_1)
    #print("Device 1 delete ")

    sensor_handler = threading.Thread(target=sensor_loop)
    sensor_handler.start()

    mqtt_client.loop_start()
    sensor_handler.join()