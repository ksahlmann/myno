# preload VD description, extract infos from device descriptions and return them to vd-mqttclient

import os
from rdflib import Graph, URIRef, Variable, Literal
from rdflib.namespace import RDF, RDFS
from rdflib import Namespace
from rdflib.plugin import register, Parser
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugin import register, Serializer
import traceback
from rdflib.namespace import RDF, OWL, XSD

register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')

import logging
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

#VD_UUID = "VIRTUAL_DEVICE-6D57-8K8K-5F12-1A8U3B1S74CC"

uuid_set = set()
topics_set = set()
sensor_topics_set = set()
conf_topics_set = set()
event_topics_set = set()
auto_topics_set = set()


initNs = {"rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#", "base":"http://yang-netconf-mqtt#", "onem2m":"http://www.onem2m.org/ontology/Base_Ontology/base_ontology#",
          "om-2":"http://www.ontology-of-units-of-measure.org/resource/om-2/", "time":"http://www.w3.org/2006/time#"}
# method with Namespace
n = Namespace("http://yang-netconf-mqtt#")
onem2m = Namespace("http://www.onem2m.org/ontology/Base_Ontology/base_ontology#")

uriref_named_individual = URIRef('http://www.w3.org/2002/07/owl#NamedIndividual')
uriref_control_func = URIRef(onem2m + 'ControllingFunction')
uriref_measure_func = URIRef(onem2m + 'MeasuringFunction')
uriref_device = URIRef(onem2m + 'Device')
uriref_serv = URIRef(onem2m + 'Service')
uriref_prop_expFunc = URIRef(onem2m + 'exposesFunctionality')
uriref_prop_hasfunc = URIRef(onem2m + 'hasFunctionality')
uriref_prop_device_thing = URIRef(onem2m + 'hasThingProperty')
uriref_prop_serv = URIRef(onem2m + "hasService")
uriref_prop_thing = URIRef(onem2m + 'ThingProperty')
uriref_yang_desc = URIRef(onem2m + 'YangDescription')
uriref_prop_value = URIRef(onem2m + 'hasValue')


def get_auto_functions(g):
    print("get_auto_functions")

    q = prepareQuery('SELECT DISTINCT ?autofunc ?topic ?method '
        'WHERE { ?device onem2m:hasFunctionality ?autofunc . ?autofunc rdf:type base:AutomationFunctionality . '
        '?autofunc onem2m:hasCommand ?cmd . ?op onem2m:exposesCommand ?cmd . ?op base:mqttTopic ?topic . ?op base:mqttMethod ?method.}',
        initNs)
    result = g.query(q)
    for row in result:
        print(" %s %s %s" % row)

    print(result.serialize(format='json'))

    return result

def get_event_functions(g):
    print("get_event_functions")

    q = prepareQuery(
        'SELECT ?eventfunc ?topic WHERE { ?device onem2m:hasFunctionality ?eventfunc . ?eventfunc rdf:type base:EventFunctionality. '
        '?serv onem2m:exposesFunctionality ?eventfunc . ?serv onem2m:hasOutputDataPoint ?dp. ?dp  base:mqttTopic ?topic. }',
        initNs)

    result = g.query(q)
    for row in result:
        print(" %s %s" % row)

    print(result.serialize(format='json'))

    return result

def get_configuration_functions(g):
    print("get_configuration_functions")

    q = prepareQuery('SELECT DISTINCT ?configurationfunc ?topic ?method '
        'WHERE { ?device onem2m:hasFunctionality ?configurationfunc . ?configurationfunc rdf:type base:ConfigurationFunctionality . '
        '?configurationfunc onem2m:hasCommand ?cmd . ?op onem2m:exposesCommand ?cmd . ?op base:mqttTopic ?topic . ?op base:mqttMethod ?method.}',
        initNs)
    result = g.query(q)
    for row in result:
        print(" %s %s %s" % row)

    print(result.serialize(format='json'))

    return result

def get_measuring_functions(g):
    print("get_measuring_functions")

    q = prepareQuery(
        'SELECT ?measuringfunc ?topic WHERE { ?device onem2m:hasFunctionality ?measuringfunc . ?measuringfunc rdf:type onem2m:MeasuringFunctionality . '
        '?serv onem2m:exposesFunctionality ?measuringfunc . ?serv onem2m:hasOutputDataPoint ?dp. ?dp  base:mqttTopic ?topic. }',
        initNs)

    result = g.query(q)
    for row in result:
        print(" %s %s" % row)

    print(result.serialize(format='json'))

    return result

def get_control_functions(g):
    print("get_control_functions")

    q = prepareQuery(
        'SELECT DISTINCT ?controlfunc ?topic ?method WHERE { ?device onem2m:hasFunctionality ?controlfunc . ?controlfunc rdf:type onem2m:ControllingFunctionality . '
        '?controlfunc onem2m:hasCommand ?cmd . ?op onem2m:exposesCommand ?cmd . ?op base:mqttTopic ?topic . ?op base:mqttMethod ?method. }',
        initNs)
    result = g.query(q)
    for row in result:
        print(" %s %s %s" % row)

    print(result.serialize(format='json'))

    return result

def get_dev_uuid(g):
    print("get_dev_uuid")

    q = prepareQuery(
        'SELECT DISTINCT ?property ?value WHERE { ?device  rdf:type onem2m:Device . ?device onem2m:hasThingProperty ?property . '
        '?property rdf:type onem2m:ThingProperty . ?property rdf:type ?type. ?property onem2m:hasValue ?value . FILTER REGEX (str(?property), "uuid", "i").}',
        initNs)
    result = g.query(q)
    for row in result:
        print(" %s %s" % row)
        uuid = row['value']

    print(result.serialize(format='json'))
    return uuid

def generate_vd_description(uuid, ctrl_func, measure_func, conf_func, event_func, auto_func):
    print("generate_vd_description")

    # preload virtual device ontology
    vdg = Graph()
    #TODO only once on program start
    file = 'ontology/preload.owl'
    # check if file not empty
    if os.path.exists(file) and os.path.getsize(file) > 0:
        vdg.parse(file, format="json-ld")

    # generate mqtt_command_mapping
    mqtt_commands = {}
    for row in ctrl_func:
        mqtt_commands[uuid] = (row['controlfunc'], row['topic'], row['method'])
        #crop actuator/pump/pump_1/UUID
        topics_set.add(str(row['topic']).rstrip(uuid))

    for row in measure_func:
        mqtt_commands[uuid] = (row['measuringfunc'], row['topic'])
        #crop sensor/humidity/humidity_1/UUID
        sensor_topics_set.add(str(row['topic']).rstrip(uuid))

    for row in conf_func:
        mqtt_commands[uuid] = (row['configurationfunc'], row['topic'], row['method'])
        # config/sensor/moisture/moisture_1/%s
        conf_topics_set.add(str(row['topic']).rstrip(uuid))

    for row in event_func:
        mqtt_commands[uuid] = (row['eventfunc'], row['topic'])
        # event/sensor/moisture/moisture_1/%s
        event_topics_set.add(str(row['topic']).rstrip(uuid))

    for row in auto_func:
        mqtt_commands[uuid] = (row['autofunc'], row['topic'], row['method'])
        # automation/sensor/moisture/moisture_1/%s
        auto_topics_set.add(str(row['topic']).rstrip(uuid))

    # searialize into JSON-LD
    vdg.serialize(destination='ontology/vd-ontology.owl', format='json-ld')

    #save & return to MQTT
    with open("ontology/vd-ontology.owl") as data_file:
        data2 = data_file.read()
        print(data2)

    return topics_set, sensor_topics_set, conf_topics_set, event_topics_set, auto_topics_set, str(data2)


def process_description(uuid, msg):
    print("process_description")

    # process incoming ontology
    g = Graph()
    g.parse(data=msg, format="json-ld", base="http://yang-netconf-mqtt#")
    # add UUID to a list
    #uuid = get_dev_uuid(g)
    #uuid_set.add(uuid)

    # does this ontology has following ctrl functions, then add mqttTopic and mqttMethod, and parameters
    ctrl_func = get_control_functions(g)
    # does this ontology has following measure functions, then add mqttTopic
    measure_func = get_measuring_functions(g)

    # does this ontology has configuration functions which generate events, then add mqttTopic and parameters
    conf_func = get_configuration_functions(g)
    event_func = get_event_functions(g)

    # does this ontology has automation functions, then add mqttTopic and parameters
    auto_func = get_auto_functions(g)

    try:
        topics_set, sensor_topics_set, conf_topics_set, event_topics_set, auto_topics_set, vdd = generate_vd_description(uuid, ctrl_func, measure_func, conf_func, event_func, auto_func)
    except Exception as err:
        track = traceback.format_exc()
        print(track)

    print("FINISHED AGGREGATION")

    return uuid, topics_set, sensor_topics_set, conf_topics_set, event_topics_set, auto_topics_set, vdd


