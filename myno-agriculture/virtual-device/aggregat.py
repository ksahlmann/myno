
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

#uriref_abstract_func = URIRef('https://www.cs.uni-potsdam.de/bs/research/myno#AbstractSwitchOffFunctionality')
#uriref_prop_hascontrolfunc = URIRef('https://www.cs.uni-potsdam.de/bs/research/myno#hasControllingFunction')
#uriref_prop_hasmeasuringfunc = URIRef('https://www.cs.uni-potsdam.de/bs/research/myno#hasMeasuringFunction')


def get_all_functions(msg):
    print("get_all_functions")
    q = prepareQuery(
        'SELECT ?device ?measuringfunc ?controlfunc WHERE {{?device onem2m:hasFunctionality ?measuringfunc . ?measuringfunc rdf:type onem2m:MeasuringFunctionality .} UNION {?device onem2m:hasFunctionality ?controlfunc . ?controlfunc rdf:type onem2m:ControllingFunctionality .}}',
        initNs)
#    FILTER REGEX(str(?measuringfunc), "f.*t", "i").

    g = Graph()
    g.parse(data=msg, format="json-ld")
    result = g.query(q)
    for row in result:
        print("%s hasMeasuringfuncFunction %s hasControllingFunction %s" % row)

    print(result.serialize(format='json'))
    return result

def get_measuring_functions(msg):
    print("get_measuring_functions")

    q = prepareQuery(
        'SELECT ?measuringfunc WHERE { ?device onem2m:hasFunctionality ?measuringfunc . ?measuringfunc rdf:type onem2m:MeasuringFunctionality . FILTER REGEX (str(?measuringfunc), "get", "i").}',
        initNs)

    g = Graph()
    g.parse(data=msg, format="json-ld")
    result = g.query(q)
    for row in result:
        print(" %s " % row)

    print(result.serialize(format='json'))

    return  result

def get_control_functions(msg):
    print("get_control_functions")

    q = prepareQuery(
        'SELECT DISTINCT ?controlfunc WHERE { ?device onem2m:hasFunctionality ?controlfunc . ?controlfunc rdf:type onem2m:ControllingFunctionality . FILTER REGEX (str(?controlfunc), "pump", "i").}',
        initNs)
    g = Graph()
    g.parse(data=msg, format="json-ld")
    result = g.query(q)
    for row in result:
        print(" %s " % row)

    print(result.serialize(format='json'))
    return result


def generate_vd_description(ctrl_func, measure_func):
    print("generate_vd_description")

    #build new graph
    vdg = Graph()

    # file = 'ontology/vd-ontology.owl'
    # # check if file not empty
    # if os.path.exists(file) and os.path.getsize(file) > 0:
    #     vdg.parse(file, format="json-ld")

    if len(vdg) == 0:
        #add vd device
        n.virtualDevice
        vdg.add((n.virtualDevice,RDF.type,uriref_named_individual))
        vdg.add((n.virtualDevice,RDF.type,uriref_device))

    #add device category
    n.vdCategory
    vdg.add((n.virtualDevice, uriref_prop_device_thing, n.vdCategory))
    vdg.add((n.vdCategory, RDF.type, uriref_named_individual))
    vdg.add((n.vdCategory, RDF.type, uriref_prop_thing))
    vdg.add((n.vdCategory, uriref_prop_value, Literal('Virtual-Device')))

    n.deviceId
    vdg.add((n.virtualDevice, uriref_prop_device_thing, n.deviceId))
    vdg.add((n.deviceId, RDF.type, uriref_named_individual))
    vdg.add((n.deviceId, RDF.type, uriref_prop_thing))
    vdg.add((n.deviceId, uriref_prop_value, Literal('VIRTUAL_DEVICE-6D57-8K8K-5F12-1A8U3B1S74CC')))

    #add deviceDesc
    n.vdDesc
    vdg.add((n.virtualDevice, uriref_prop_device_thing, n.vdDesc))
    vdg.add((n.vdDesc, RDF.type, uriref_yang_desc))
    vdg.add((n.vdDesc, uriref_prop_value, Literal('Aggregated Device on the Edge')))

    #add service
    n.servVDnetconf
    vdg.add((n.virtualDevice, uriref_prop_serv, n.servVDnetconf))
    vdg.add((n.servVDnetconf, RDF.type, uriref_serv))

    #method with Variable like in rdflib.query.ResultRow
    #add measuring functions & services
    if ctrl_func:
        for row in ctrl_func:
            line = row['controlfunc']
            if line is not None:
                print("%s" % row['controlfunc'])
                vdg.add((n.virtualDevice, uriref_prop_hasfunc, line))
                vdg.add((line, RDF.type, uriref_control_func))
                vdg.add((n.servVDnetconf, uriref_prop_expFunc, line))

    if measure_func:
        for row in measure_func:
            line = row['measuringfunc']
            if line is not None:
                print("%s" % row['measuringfunc'])
                vdg.add((n.virtualDevice, uriref_prop_hasfunc, line))
                vdg.add((line, RDF.type, uriref_measure_func))
                vdg.add((n.servVDnetconf, uriref_prop_expFunc, line))

    # aggregate
    aggregate_functions(vdg)

    # searialize into JSON-LD
    vdg.serialize(destination='ontology/vd-ontology.owl', format='json-ld')

    #save & return to MQTT
    with open("ontology/vd-ontology.owl") as data_file:
        data2 = data_file.read()
        print(data2)

    return str(data2)


def aggregate_functions(vdg):
    print("aggregate_functions")

    # TODO aggregate functions like one switchAllOn and switchAllOff and map
    # TODO kann nichts finden, weil in device1 verschiedene namespaces bei den instanzen verwendet werden. WARUM und WAS IST RICHTIG?
    q = prepareQuery(
        'SELECT ?controlfunc WHERE { ?device onem2m:hasFunctionality ?controlfunc . ?controlfunc rdf:type onem2m:ControllingFunction . FILTER REGEX (str(?controlfunc), "off", "i").}',
        initNs)
    result = vdg.query(q)
    if len(result) > 0:
        for row in result:
            print("off %s" % row)
            line = row['controlfunc']
            vdg.remove((n.virtualDevice, uriref_prop_hasfunc, line))
            vdg.remove((n.servVDnetconf, uriref_prop_expFunc, line))
            vdg.remove((line, RDF.type, uriref_control_func))

            # replace controllingFunction
            vdg.add((n.virtualDevice, uriref_prop_hasfunc, line + 'All'))
            vdg.add((n.servVDnetconf, uriref_prop_expFunc, line + 'All'))
            vdg.add((line + 'All', RDF.type, uriref_control_func))

        # n.switchAllOff
        # vdg.add((uriref_prop_hasfunc, RDFS.subClassOf, uriref_control_func))
        # vdg.add((n.switchAllOff, RDF.type, uriref_named_individual))
        # vdg.add((n.switchAllOff, RDF.type, uriref_prop_hasfunc))
        # vdg.add((n.virtualDevice, uriref_prop_hasfunc, n.switchAllOff))
        # for row in result:
        #     # add sub-functions for mapping
        #     sub_func = URIRef(n + 'hasFunctionality')
        #     if row['controlfunc'] != n.switchAllOff:
        #         vdg.add((n.switchAllOff, sub_func, row['controlfunc']))


def process_description(msg):
    # all functions
    #functions = get_all_functions(msg)
    #data = generate_vd_description(functions)

    # ctrl functions
    ctrl_func = get_control_functions(msg)
    measure_func = get_measuring_functions(msg)
    try:
        data = generate_vd_description(ctrl_func, measure_func)
    except Exception as err:
        track = traceback.format_exc()
        print(track)

    print("FINISHED AGGREGATION")

    return data


