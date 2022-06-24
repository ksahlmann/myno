import time
import random
import threading
import paho.mqtt.client as mqtt


threadLock = threading.Lock()
DEVICE_UUID1 = "SIMULATOR1-8A12-4F4F-8F69-6B8F3C2E78DD"
DEVICE_UUID2 = "SIMULATOR2-5B34-7D7D-3K87-5H2G6U5K19RR"

BROKER_ADDR = "localhost"
#BROKER_ADDR = "192.168.0.110"
BROKER_PORT = 1883

ONTOLOGY_FILE_1 = "ontology/device1.owl"
ONTOLOGY_FILE_2 = "ontology/device2.owl"

CONFIG_TOPIC = 'yang/config'
CREATE_TOPIC = 'yang/config/create'
UPDATE_TOPIC = 'yang/config/update'

CMD_TOPIC1 = 'actuator/led/led_1/'+DEVICE_UUID1
CMD_TOPIC2 = 'actuator/pump/pump_1/'+DEVICE_UUID2
SENSOR_TOPIC1 = "sensor/humidity/humidity_1/" + DEVICE_UUID1
SENSOR_TOPIC2 = "sensor/humidity/humidity_1/" + DEVICE_UUID2
SENSOR_TOPIC3 = "sensor/temperature/temperature_1/" + DEVICE_UUID1
SENSOR_TOPIC4 = "sensor/temperature/temperature_1/" + DEVICE_UUID2

RESPONSE_TOPIC1 = 'response/'+DEVICE_UUID1
RESPONSE_TOPIC2 = 'response/'+DEVICE_UUID2

STATE = "OFF"

def mqtt_connect(mqtt_client, userdata, flags, rc):
    mqtt_client.subscribe(CMD_TOPIC1 + DEVICE_UUID1)
    mqtt_client.subscribe(CMD_TOPIC2 + DEVICE_UUID1)

def mqtt_message(mqtt_client, userdata, msg):
    global STATE
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
        mqtt_client.publish(RESPONSE_TOPIC1, seq_id+";NOOP")
    elif cmd in {"ON", "OFF", "GREEN", 'orange', 'all', 'yellow', 'green', 'red'}:
        print("CTRL RECEIVED, STATE SWITCH: "+STATE+" -> "+cmd)
        STATE = cmd
        mqtt_client.publish(RESPONSE_TOPIC1, seq_id+";OK")
    else:
        print("CTRL RECEIVED, UNKNOWN CTRL")
        mqtt_client.publish(RESPONSE_TOPIC1, seq_id+";ERROR")

def sensor_loop():
    while True:
        mqtt_client.publish(SENSOR_TOPIC1, random.randint(0,100))
        mqtt_client.publish(SENSOR_TOPIC2, random.randint(0, 100))
        time.sleep(5)
        mqtt_client.publish(SENSOR_TOPIC3, random.randint(0, 50))
        mqtt_client.publish(SENSOR_TOPIC4, random.randint(0, 50))
        time.sleep(5)


if __name__ == "__main__":
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = mqtt_connect
    mqtt_client.on_message = mqtt_message

    mqtt_client.connect(BROKER_ADDR, BROKER_PORT, 60)

    # with open(ONTOLOGY_FILE_1) as data_file:
    #     ontology1 = DEVICE_UUID1 + ";" + (data_file.read().replace('%s', DEVICE_UUID1 ))
    #     #ontology1 = DEVICE_UUID1 + ";" + data_file.read()
    #     mqtt_client.publish(CREATE_TOPIC, ontology1)
    #     mqtt_client.publish(CREATE_TOPIC, DEVICE_UUID1 + ";END")
    #     print("Ontology 1 published")
    #
    #
    # time.sleep(5)
    #
    #
    # with open(ONTOLOGY_FILE_2) as data_file:
    #     ontology2 = DEVICE_UUID2 + ";" + (data_file.read().replace('%s', DEVICE_UUID2 ))
    #     #ontology2 = DEVICE_UUID2 + ";" + data_file.read()
    #     mqtt_client.publish(CREATE_TOPIC, ontology2)
    #     mqtt_client.publish(CREATE_TOPIC, DEVICE_UUID2 + ";END")
    #     print("Ontology 2 published")

    time.sleep(10)

    with open(ONTOLOGY_FILE_2) as data_file:
        ontology2 = DEVICE_UUID2 + ";" + (data_file.read().replace('%s', DEVICE_UUID2 ))
        #ontology2 = DEVICE_UUID2 + ";" + data_file.read()
        mqtt_client.publish(UPDATE_TOPIC, ontology2)
        mqtt_client.publish(UPDATE_TOPIC, DEVICE_UUID2 + ";END")
        print("Ontology 2 published")


    # with open(ONTOLOGY_FILE_1) as data_file:
    #     #ontology = DEVICE_UUID1 + ";" + (data_file.read() % (DEVICE_UUID1, SENSOR_TOPIC1))
    #     ontology1 = DEVICE_UUID1 + ";" + data_file.read()
    #     print(ontology1)
    #     mqtt_client.publish(CONFIG_TOPIC, ontology1)
    #     mqtt_client.publish(CONFIG_TOPIC,  DEVICE_UUID1+";END")
    #     print("Ontology 1 published")
    #
    # with open(ONTOLOGY_FILE_2) as data_file2:
    #     #print(data_file2.read())
    #     #ontology = DEVICE_UUID2+";"+(data_file.read() % (DEVICE_UUID2, SENSOR_TOPIC2))
    #     ontology2 = DEVICE_UUID2 + ";" + data_file2.read()
    #     print(ontology2)
    #     mqtt_client.publish(CONFIG_TOPIC, ontology2)
    #     mqtt_client.publish(CONFIG_TOPIC,  DEVICE_UUID2+";END")
    #     print("Ontology 2 published")

    sensor_handler = threading.Thread(target=sensor_loop)
    sensor_handler.start()

    mqtt_client.loop_start()
    sensor_handler.join()