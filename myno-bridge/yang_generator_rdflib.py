# August 2018-2020, Kristina Sahlmann <sahlmann@uni-potsdam.de>

import time
import traceback
import pyang
import pyang.plugin
from pyang.statements import Statement
from optparse import OptionParser
from io import StringIO
from rdflib import Graph
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugin import register, Parser
register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')

deviceList = []
serviceList = []
outDpList = []
ctrlfuncList = []
measurefuncList = []
opList = []
opStateList = []
cmdList = []
inputList = []
outputList = []
propList = []

# adjust namespace for your ontology
#yang_namespace = "https://www.cs.uni-potsdam.de/bs/research/myno/"
yang_namespace = "http://yang-netconf-mqtt#"
initNs = {"rdf":"http://www.w3.org/1999/02/22-rdf-syntax-ns#", "base":"http://yang-netconf-mqtt#", "onem2m":"http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}

generic_value = '@value'
generic_id = '@id'
generic_type = '@type'
generic_list = '@list'

custom_types = {}
custom_base = 'http://yang-netconf-mqtt'
custom_deviceCategory = custom_base + '#deviceCategory'
custom_deviceDescription = custom_base + '#deviceDesc'
custom_deviceUUID = custom_base + '#deviceUuid'
custom_mqttMethod = custom_base + '#mqttMethod'
custom_mqttTopic = custom_base + '#mqttTopic'
custom_descriptionType = custom_base + '#YangDescription'
# custom_returnType = "returnType"

oneM2M_base = 'http://www.onem2m.org/ontology/Base_Ontology/base_ontology'
oneM2M_device = oneM2M_base + '#Device'
oneM2M_service = oneM2M_base + '#Service'
oneM2M_controllingFunctionality = oneM2M_base + '#ControllingFunctionality'
oneM2M_measuringFunctionality = oneM2M_base + '#MeasuringFunctionality'
oneM2M_hasFunctionality = oneM2M_base + '#hasFunctionality'
oneM2M_exposesFunctionality = oneM2M_base + '#exposesFunctionality'
oneM2M_Operation = oneM2M_base + '#Operation'
oneM2M_hasOperation = oneM2M_base + '#hasOperation'
oneM2M_ThingProperties = oneM2M_base + '#ThingProperty'
oneM2M_hasThingProperties = oneM2M_base + '#hasThingProperty'
oneM2M_OperationInput = oneM2M_base + '#OperationInput'
oneM2M_OperationOutput = oneM2M_base + '#OperationOutput'
oneM2M_Command = oneM2M_base + '#Command'
oneM2M_hasCommand = oneM2M_base + '#hasCommand'
oneM2M_exposesCommand = oneM2M_base + '#exposesCommand'
oneM2M_hasValue = oneM2M_base + '#hasValue'
oneM2M_hasService = oneM2M_base + '#hasService'
oneM2M_hasSubService = oneM2M_base + '#hasSubService'
oneM2M_hasInput = oneM2M_base + '#hasInput'
oneM2M_hasOutput = oneM2M_base + '#hasOutput'
oneM2M_OutputDataPoint = oneM2M_base + '#OutputDataPoint'
oneM2M_hasOutputDataPoint = oneM2M_base + '#hasOutputDataPoint'
oneM2M_hasDataRestriction_pattern = oneM2M_base + '#hasDataRestriction_pattern'
oneM2M_OperationState = oneM2M_base + '#OperationState'
oneM2M_hasOperationState = oneM2M_base + '#hasOperationState'

owl_namedIndividual = 'http://www.w3.org/2002/07/owl#NamedIndividual'
owl_oneOf = 'http://www.w3.org/2002/07/owl#oneOf'
owl_equivalentClass = 'http://www.w3.org/2002/07/owl#equivalentClass'
rdf_datatype = "http://www.w3.org/2000/01/rdf-schema#Datatype"

yang_namespace = "https://www.cs.uni-potsdam.de/bs/research/myno/"
yang_prefix = "led"


##### START ONEM2M
def checkOneM2MType(item, itype):
    if generic_type in item:
        return itype in item[generic_type]
    return False


def checkOneM2MID(item, _id):
    if generic_id in item:
        return _id == item[generic_id]
    return False


def getOneM2MEntry(item, entryType, returnList=False):
    if entryType in item:
        if returnList or len(item[entryType]) > 1:
            return item[entryType]
        else:
            if isinstance((item[entryType]), str):
                return (item[entryType])
            else:
                if generic_value in item[entryType][0]:
                    return item[entryType][0][generic_value]
                else:
                    return item[entryType][0]
    return None


def getEntityfromID(_id, data):
    for i in data:
        if checkOneM2MID(i, _id):
            return i
    return None


def getIDsfromContainer(container, itype):
    ids = []

    rawList = getOneM2MEntry(container, itype, returnList=True)
    if rawList != None:
        for i in rawList:
            ids.append(getOneM2MEntry(i, generic_id))

    return ids


def createReferences(idlist, items):
    for i in items:
        for n, _id in enumerate(idlist):
            if i['id'] == _id:
                idlist[n] = i

##### END ONEM2M

def getValueFromID(list, id):
    for i in list:
        if i['id'] == id:
            return i['values'][0]


def getDescriptionFromItem(item):
    return getDescriptionFromList(item['properties'])


def getDescriptionFromList(_list):
    for i in _list:
        if i['type'] == custom_descriptionType:
            if 'values' in i:
                return i['values']
            if 'dataRestrictions' in i:
                return i['dataRestrictions']
    return None


##### START YANG
class DummyRepository(pyang.Repository):
    """Dummy implementation of abstract :class:`pyang.Repository`
       for :class:`pyang.Context` instantiations
    """

    def get_modules_and_revisions(self, ctx):
        """Just a must-have dummy method, returning empty ``tuple``.
        Modules are directly given to pyang output plugins

        """
        return ()


def generateYangForDevice(device):
    uuid = getValueFromID(device['properties'], custom_deviceUUID)

    devstate = Statement(None, None, None, 'container', 'device')

    # add description
    devstate.substmts.append(
        Statement(None, None, None, u'description', getValueFromID(device['properties'], custom_deviceDescription)))

    # add id subtree
    idstate = Statement(None, None, None, 'list', 'device-id')
    idstate.substmts.append(Statement(None, None, None, 'key', u'uuid'))
    idstatesub = Statement(None, None, None, 'leaf', u'uuid')
    idstatesub.substmts.append(Statement(None, None, None, u'default', uuid))
    idstatesub.substmts.append(Statement(None, None, None, u'type', u'string'))
    idstate.substmts.append(idstatesub)
    devstate.substmts.append(idstate)

    # add category subtree
    catstate = Statement(None, None, None, 'leaf', u'device-category')
    catstate.substmts.append(Statement(None, None, None, u'description',
                                       u'Identifies the device category'))  # TODO add to yang or server
    catstate.substmts.append(Statement(None, None, None, u'type', u'string'))
    devstate.substmts.append(catstate)

    return devstate


def getOperationFromCommand(cmd):
    for op in opList:
        if cmd in op['commands']:
            return op
    return None


def generateYangForRPC(func):
    ID = func['id'].split("#")[1]
    state = Statement(None, None, None, 'rpc', ID)
    state.substmts.append(Statement(None, None, None, 'description', getDescriptionFromItem(func)[0]))

    inputstate = Statement(None, None, None, 'input', None)
    outputstate = Statement(None, None, None, 'output', None)
    if 'commands' in func:
        for inp in func['commands'][0]['inputs']:
            typestate = Statement(None, None, None, 'leaf', inp['id'].split("#")[1])
            typestate.substmts.append(Statement(None, None, None, u'description', getDescriptionFromItem(inp)[0]))
            if 'dataRestrictions' in inp:
                enum = Statement(None, None, None, u'type', u'enumeration')
                i = 0
                for pv in inp['dataRestrictions']:
                    eItem = Statement(None, None, None, u'enum', pv[generic_value])
                    enum.substmts.append(eItem)
                    i = i + 1
                typestate.substmts.append(enum)
            elif 'variables' in inp:
                union = Statement(None, None, None, u'type', u'union')
                #i = 0
                for var in inp['variables']:
                    for key in var:
                        eItem = Statement(None, None, None, u'type', key.split("#")[1])
                        range = Statement(None, None, None, u'range', var[key])
                        eItem.substmts.append(range)
                    union.substmts.append(eItem)
                    #i = i + 1
                typestate.substmts.append(union)
            elif 'datatype' in inp:
                if inp['datatype']:
                    if 'variable' in inp:
                        range = Statement(None, None, None, u'range', inp['variable'])
                        datatype = Statement(None, None, None, u'type', inp['datatype'])
                        datatype.substmts.append(range)
                        typestate.substmts.append(datatype)
                    else:
                        typestate.substmts.append(Statement(None, None, None, u'type', inp['datatype']))
                else:
                    typestate.substmts.append(Statement(None, None, None, u'type', u'string'))
            else:
                typestate.substmts.append(Statement(None, None, None, u'type', u'string'))

            inputstate.substmts.append(typestate)
        #        for out in func['commands'][0]['outputs']:
        #            typestate = Statement(None, None , None, 'leaf', out['id'].split("#")[1])
        #            if 'possibleValues' in out[custom_returnType]:
        #                _type = out[custom_returnType]
        #                enum = Statement(None, None , None, u'type', u'enumeration')
        #                i = 0
        #                for pv in _type['possibleValues']:
        #                    subenum = Statement(None, None , None, u'enum', pv)
        #                    subenum.substmts.append( Statement(None, None , None, u'description', getDescriptionFromItem(out)[i]))
        #                    enum.substmts.append(subenum)
        #                    i = i + 1
        #                typestate.substmts.append(enum)
        #            outputstate.substmts.append(typestate)
        op = getOperationFromCommand(func['commands'][0])
        if 'operationState' in op:
            typestate = Statement(None, None, None, 'leaf', 'retval')
            enum = Statement(None, None, None, u'type', u'enumeration')
            i = 0
            for pv in op['operationState'][0]['dataRestrictions']:
                eItem = Statement(None, None, None, u'enum', pv[generic_value])
                desc = getDescriptionFromItem(op['operationState'][0])[i]
                eItem.substmts.append(Statement(None, None, None, u'description', desc[generic_value]))
                enum.substmts.append(eItem)
                i = i + 1
            typestate.substmts.append(enum)
            outputstate.substmts.append(typestate)
        # if 'mqttTopic' in op:
        #     mqttTopic = op['mqttTopic']
        if 'inDps' in op:
            inDps = op['inDps']
    # if 'mqttTopic' in op:
    #     state.substmts.append(Statement(None, None, None, 'default', mqttTopic['@value']))

    if 'inDps' in op:
        state.substmts.append(Statement(None, None, None, 'default', inDps['@value']))

    state.substmts.append(inputstate)
    state.substmts.append(outputstate)

    return state


def generateYangForDps(svc):
    func = svc['functionalities'][0]
    ID = func['id'].split("#")[1]
    state = Statement(None, None, None, u'leaf', ID)
    state.substmts.append(Statement(None, None, None, u'description', getDescriptionFromItem(func)[0]))

    dpContainer = Statement(None, None, None, u'container', u'datapoint')
    state.substmts.append(dpContainer)
    i = 0
    for dp in svc['outDps']:
        dpstate = Statement(None, None, None, u'leaf', ID + str(i))
        dpstate.substmts.append(Statement(None, None, None, u'default', dp['mqttTopic'][generic_value]))
        dpstate.substmts.append(Statement(None, None, None, u'type', u'string'))
        if "units" in dp:
            dpstate.substmts.append(Statement(None, None, None, u'units', dp['units'][generic_value]))
        dpContainer.substmts.append(dpstate)
        i = i + 1

    return state


def recursiveAddServices(service, addlist):
    if 'subservices' in service:
        for svc in service['subservices']:
            recursiveAddServices(svc, addlist)
    addlist.append(service)
    return


def generateYang(deviceList, data):
    global telemetryContainer

    for dev in deviceList:
        category = getValueFromID(dev['properties'], custom_deviceCategory)
        result = Statement(None, None, None, u'module', u'mqtt-' + category)

        namespace = Statement(None, result, None, u'namespace', yang_namespace + category)
        result.substmts.append(namespace)
        prefix = Statement(None, result, None, u'prefix', category)
        result.substmts.append(prefix)

        devstate = generateYangForDevice(dev)
        telemetryContainer = None
        # compile recursive service list
        recursiveServices = []
        for svc in dev['services']:
            recursiveAddServices(svc, recursiveServices)

        for svc in recursiveServices:
            if 'functionalities' in svc:
                for func in svc['functionalities']:
                    if 'commands' in func:
                        rpcstate = generateYangForRPC(func)
                        result.substmts.append(rpcstate)
            if 'outDps' in svc and (str(svc['outDps'][0]) != "None"):
                if (telemetryContainer is None):
                    telemetryContainer = Statement(None, None, None, u'container', u'telemetry')
                    devstate.substmts.append(telemetryContainer)
                dpstate = generateYangForDps(svc)
                telemetryContainer.substmts.append(dpstate)

        # add device to result module
        result.substmts.append(devstate)

        data.append(result)
        print("yang data: " + str(result)) #debug output
        #erg = result.search("SIMULATOR8")
        #print("search statement: " + str(erg)) #debug output

#### END YANG

#### START RDFLIB

def parseDevices(g, deviceList):
    print("parseDevices")
    q = prepareQuery(
        'SELECT DISTINCT ?device ?services ?functions ?properties WHERE {?device rdf:type onem2m:Device . ?device onem2m:hasFunctionality ?functions . ?device onem2m:hasService ?services . ?device onem2m:hasThingProperty ?properties . }',
        initNs)
    result = g.query(q)

    device = {}
    services = set([])
    functionalities = set([])
    properties = set([])
    for row in result:
        print(" %s %s %s %s" % row)
        device[generic_id] = str(row["device"])
        services.add(str(row["services"]))
        functionalities.add(str(row["functions"]))
        properties.add(str(row["properties"]))
    device['services'] = list(services)
    device['functionalities'] = list(functionalities)
    device['properties'] = list(properties)
    print(device)
    deviceList.append(device)
    return deviceList

def parseServices(g, serviceList):
    print("parseServices")

    q = prepareQuery(
        'SELECT DISTINCT ?services  ?functions  ?subservices  ?operations '
        'WHERE { ?device onem2m:hasService ?services . ?services onem2m:hasSubService ?subservices .   ?services  onem2m:exposesFunctionality ?functions . '
        ' OPTIONAL { ?services onem2m:hasOperation ?operations . } } ORDER BY DESC(?functions) ',
        initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base="http://yang-netconf-mqtt#")
    result = g.query(q)

    functionalities = set([])
    operations = set([])
    subservices = set([])
    #outDps = []
    for row in result:
        print(" %s %s %s %s" % row)
        service = {}
        service['id'] = str(row["services"])
        functionalities.add(str(row["functions"]))
        #functionalities.add(str(row["subfunctions"]))
        subservices.add(str(row["subservices"]))
        operations.add(str(row["operations"]))
        #operations.add(str(row["suboperations"]))
    service['functionalities'] = list(functionalities)
    service['operations'] = list(operations)
    service['subservices'] = list(subservices)
    print(service)
    serviceList.append(service)

    # Type 2 subservices with outDPs
    q = prepareQuery(
        'SELECT DISTINCT ?subservices ?functions ?outDps ?operations '
        'WHERE { ?services onem2m:hasSubService ?subservices . ?subservices  onem2m:exposesFunctionality ?functions . OPTIONAL {?subservices onem2m:hasOutputDataPoint ?outDps .} OPTIONAL{?subservices onem2m:hasOperation ?operations . } }  ORDER BY DESC(?functions) ',
        initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base="http://yang-netconf-mqtt#")
    result = g.query(q)

    for row in result:
        print(" %s %s %s %s" % row)
        service = {}
        service['id'] = str(row["subservices"])
        service['functionalities'] = [str(row["functions"])]
        #if(str(row["outDps"])):
        service['outDps'] = [str(row["outDps"])]
        if (str(row["operations"])):
            service['operations'] = [str(row["operations"])]  # new
        print(service)
        serviceList.append(service)
    return serviceList

    # # Type 2 subservices with operations
    # q = prepareQuery(
    #     'SELECT DISTINCT ?subservices ?functions ?operations '
    #     'WHERE { ?services onem2m:hasSubService ?subservices . ?subservices  onem2m:exposesFunctionality ?functions .  ?subservices onem2m:hasOperation ?operations . } ORDER BY DESC(?functions)  ',
    #     initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
    #     base="http://yang-netconf-mqtt#")
    # result = g.query(q)
    #
    # for row in result:
    #     print(" %s %s %s" % row)
    #     service = {}
    #     service['id'] = str(row["subservices"])
    #     service['functionalities'] = [str(row["functions"])]
    #     service['operations'] = [str(row["operations"])] #new
    #     print(service)
    #     serviceList.append(service)
    # return serviceList

def parseOutDps(g, outDpList):
    print("parseOutDps")
    q = prepareQuery(
        'SELECT DISTINCT ?outDp ?mqttTopic ?units ?symbolValue WHERE { ?services onem2m:hasOutputDataPoint ?outDp . ?outDp  base:mqttTopic ?mqttTopic . OPTIONAL { ?outDp om-2:hasUnit ?units . ?units om-2:symbol ?symbolValue . }}',
        initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#", "om-2":"http://www.ontology-of-units-of-measure.org/resource/om-2/"},
        base="http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s %s %s " % row)
        outDp = {}
        outDp['id'] = str(row["outDp"])
        outDp['mqttTopic'] = {'@value': str(row["mqttTopic"])}

        if (row["units"]):
            unitValue = str(row["units"]).split("/om-2/")[1] + ';' + str(row["symbolValue"])
            outDp['units'] = {'@value': unitValue}

        outDpList.append(outDp)
        print(outDpList)
    return outDpList

def parseInDps(g, inDpList):
    print("parseInDps")
    q = prepareQuery(
        'SELECT DISTINCT ?inDp ?mqttTopic WHERE { ?services onem2m:hasInputDataPoint ?inDp . ?inDp  base:mqttTopic ?mqttTopic . }',
        initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#" },
        base="http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s " % row)
        inDp = {}
        inDp['id'] = str(row["inDp"])
        inDp['mqttTopic'] = {'@value': str(row["mqttTopic"])}

        inDpList.append(inDp)
        print(inDpList)
    return inDpList


def parseCtrlFunctionality(g, ctrlfuncList):
    print("parseCtrlFunctionality")
    q = prepareQuery(
        'SELECT DISTINCT ?ctrlFunction ?command ?property WHERE { ?ctrlFunction rdf:type onem2m:ControllingFunctionality . ?ctrlFunction onem2m:hasCommand ?command . ?ctrlFunction onem2m:hasThingProperty ?property .}',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
                     base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s %s " % row)
        func = {}
        func['id'] = str(row["ctrlFunction"])
        func['commands'] = [str(row["command"])]
        func['properties'] = [str(row["property"])]
        ctrlfuncList.append(func)
        print(ctrlfuncList)
    return ctrlfuncList


def parseConfigFunctionality(g, configfuncList):
    print("parseConfigFunctionality")
    q = prepareQuery(
        'SELECT DISTINCT ?configFunction ?command ?property WHERE { ?configFunction rdf:type base:ConfigurationFunctionality . ?configFunction onem2m:hasCommand ?command . ?configFunction onem2m:hasThingProperty ?property .}',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
                     base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s %s " % row)
        func = {}
        func['id'] = str(row["configFunction"])
        func['commands'] = [str(row["command"])]
        func['properties'] = [str(row["property"])]
        configfuncList.append(func)
        print(configfuncList)
    return configfuncList

def parseAutomationFunctionality(g, autofuncList):
    print("parseAutomationFunctionality")
    q = prepareQuery(
        'SELECT DISTINCT ?autoFunction ?command ?property WHERE { ?autoFunction rdf:type base:AutomationFunctionality . ?autoFunction onem2m:hasCommand ?command . ?autoFunction onem2m:hasThingProperty ?property .}',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
                     base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s %s " % row)
        func = {}
        func['id'] = str(row["autoFunction"])
        func['commands'] = [str(row["command"])]
        func['properties'] = [str(row["property"])]
        autofuncList.append(func)
        print(autofuncList)
    return autofuncList

def parseMeasureFunctionality(g, measurefuncList):
    print("parseMeasureFunctionality")

    q = prepareQuery(
        'SELECT DISTINCT ?ctrlFunction ?property WHERE { ?ctrlFunction rdf:type onem2m:MeasuringFunctionality .  ?ctrlFunction onem2m:hasThingProperty ?property .}',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
                     base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s " % row)
        func = {}
        func['id'] = str(row["ctrlFunction"])
        func['properties'] = [str(row["property"])]
        measurefuncList.append(func)
        print(measurefuncList)
    return measurefuncList


def parseEventFunctionality(g, eventfuncList):
    print("parseEventFunctionality")

    q = prepareQuery(
        'SELECT DISTINCT ?eventFunction ?property WHERE { ?eventFunction rdf:type base:EventFunctionality .  ?eventFunction onem2m:hasThingProperty ?property .}',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
                     base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s " % row)
        func = {}
        func['id'] = str(row["eventFunction"])
        func['properties'] = [str(row["property"])]
        eventfuncList.append(func)
        print(eventfuncList)
    return eventfuncList


def parseOpStates(g, opStateList):
    print("parseOpStates")

    q = prepareQuery(
        'SELECT DISTINCT ?opState ?statePattern ?opStateDesc ' 
        'WHERE { ?operation onem2m:hasOperationState ?opState . ?opState rdf:type onem2m:OperationState . ' 
        '?opState onem2m:hasThingProperty ?opStateDesc . ?opState onem2m:hasDataRestriction_pattern ?statePattern .} ORDER BY ?statePattern  ',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")
    opstate = {}
    statePattern = []
    for row in result:
        print(" %s %s %s" % row)
        opstate['id'] = str(row["opState"])
        opstate['properties'] = [str(row["opStateDesc"])]
        statePattern.append({'@value' : str(row["statePattern"])})
    opstate['dataRestrictions'] = statePattern
    opStateList.append(opstate)
    print(opStateList)
    return opStateList


def parseOperations(g, opList):
    print("parseOperations")

    q = prepareQuery(
        'SELECT DISTINCT ?operation ?command ?inputs ?opState ?mqttMethod ?mqttTopic ?inDps '
        'WHERE { ?service onem2m:hasOperation ?operation . ?operation onem2m:hasOperationState ?opState . '
        '?operation onem2m:exposesCommand ?command . ?operation onem2m:hasInput ?inputs . '
        '?operation base:mqttTopic ?mqttTopic. ?operation base:mqttMethod ?mqttMethod . OPTIONAL{ ?operation onem2m:hasInputDataPoint ?operationInput.  ?operationInput base:mqttTopic ?operationInputTopic . } '
        'OPTIONAL{?operation onem2m:hasInputDataPoint ?inputPoint. ?inputPoint base:mqttTopic ?inDps . } } ORDER BY ?operation ',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")
    for row in result:
        print(" %s %s %s %s %s %s %s" % row)
        operation = str(row["operation"])
        if(len(opList) == 0):
            op = {}
            op['id'] = str(row["operation"])
            op['commands'] = [str(row["command"])]
            op['inputs'] = [str(row["inputs"])]
            op['operationState'] = [str(row["opState"])]
            op['mqttMethod'] = {'@value' : str(row["mqttMethod"])}
            op['mqttTopic'] = {'@value' : str(row["mqttTopic"])}
            if(row["inDps"]):
                op['inDps'] = {'@value' : str(row["inDps"])}
            opList.append(op)
        else:
            #is operation already included?
            tmp = False
            for op in opList :
                if(op['id'] == operation):
                    #add further input
                    op['inputs'].append(str(row["inputs"]))
                    tmp = True
            if(tmp == False):
                op = {}
                op['id'] = str(row["operation"])
                op['commands'] = [str(row["command"])]
                op['inputs'] = [str(row["inputs"])]
                op['operationState'] = [str(row["opState"])]
                op['mqttMethod'] = {'@value': str(row["mqttMethod"])}
                op['mqttTopic'] = {'@value': str(row["mqttTopic"])}
                if (row["inDps"]):
                    op['inDps'] = {'@value': str(row["inDps"])}
                opList.append(op)
    print(opList)
    return opList


def parseCommands(g, cmdList):
    print("parseCommands")

    q = prepareQuery(
        'SELECT DISTINCT ?command ?inputs ' 
        'WHERE { ?function onem2m:hasCommand ?command . ?command onem2m:hasInput ?inputs . } ORDER BY ?inputs',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")
    for row in result:
        print(" %s %s " % row)
        command = str(row["command"])
        if(len(cmdList) == 0):
            cmd = {}
            cmd['id'] = command
            cmd['inputs'] = [str(row["inputs"])]
            cmdList.append(cmd)
        else:
            #ist command schon drin? dann nur noch inputs ergaenzen
            tmp = False
            for c in cmdList:
                if(c['id'] == command):
                    c['inputs'].append(str(row["inputs"]))
                    tmp = True
            if(tmp == False):
                cmd = {}
                cmd['id'] = command
                cmd['inputs'] = [str(row["inputs"])]
                cmdList.append(cmd)
    # cmd['outputs'] = [str(row["outputs"])]
    print(cmdList)
    return cmdList


def parseInputs(g, inputList):
    print("parseInputs")
    # inputs with optional DataRestriction_pattern
    q = prepareQuery(
        'SELECT DISTINCT ?input ?properties ?dataRestrictions '
        'WHERE { ?command onem2m:hasInput ?input . OPTIONAL { ?input onem2m:hasThingProperty ?properties . } OPTIONAL{ ?input onem2m:hasDataRestriction_pattern ?dataRestrictions .} } ORDER BY ?input ',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s %s " % row)
        inp = str(row["input"])
        if(len(inputList) == 0):
            input = {}
            input['id'] = str(row["input"])
            #if(row["properties"]):
            input['properties'] = [str(row["properties"])]
            # several or none dataRestrictions
            if (row["dataRestrictions"]):
                input['dataRestrictions'] = [{'@value': str(row["dataRestrictions"])}]
            inputList.append(input)
        else:
            # is input already in the list? then add further  dataRestrictions
            tmp = False
            for i in inputList:
                if(i['id'] == inp and str(row["dataRestrictions"])):
                    i['dataRestrictions'].append({'@value': str(row["dataRestrictions"])})
                    tmp = True
            if(tmp == False):
                input = {}
                input['id'] = str(row["input"])
                #if (row["properties"]):
                input['properties'] = [str(row["properties"])]
                # several or none dataRestrictions
                if (row["dataRestrictions"]):
                    input['dataRestrictions'] = [{'@value': str(row["dataRestrictions"])}]
                inputList.append(input)

    # inputs with subStructure
    q = prepareQuery(
        'SELECT DISTINCT ?input ?properties ?variable ?min ?max '
        'WHERE { ?command onem2m:hasInput ?input . ?input onem2m:hasThingProperty ?properties . ?input onem2m:hasSubStructure ?variable . ?variable onem2m:hasDataRestriction_minInclusive ?min . ?variable onem2m:hasDataRestriction_maxInclusive ?max . } ORDER BY ?input ',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")

    # substructure
    for row in result:
        print(" %s %s %s %s %s " % row)
        inp = str(row["input"])
    # input is already in the list. only add variables
        for i in inputList:
            if (i['id'] == inp and str(row["variable"])):
                if('variables' not in i):
                    # first addition
                    i['variables'] = [{str(row["variable"]): (str(row["min"]) + '..' + str(row["max"]))}]
                else:
                    i['variables'].append({str(row["variable"]): (str(row["min"]) + '..' + str(row["max"]))})


    # inputs with datatype
    #TODO
    q = prepareQuery(
        'SELECT DISTINCT ?input ?prop ?datatype ?min ?max '
        'WHERE { ?command rdf:type onem2m:Command . ?command onem2m:hasInput ?input . OPTIONAL {?input onem2m:hasInput ?prop .  OPTIONAL {?prop  onem2m:hasDataType ?datatype . }OPTIONAL {?prop onem2m:hasDataRestriction_minInclusive ?min . ?prop onem2m:hasDataRestriction_maxInclusive ?max . }}} ORDER BY ?input ',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")

    # datatypes
    print("parse inputs with datatypes")
    for row in result:
        print(" %s %s %s %s %s" % row)
        inp = str(row["input"])
    # input is already in the list. only add datatypes
        for i in inputList:
            if (i['id'] == inp ):
                if(row["datatype"]):
                    datatype = str(row["datatype"]).split("#")[1]
                    if ('datatype' not in i):
                        # first addition
                        i['datatype'] = datatype
                    else:
                        i['datatype'].append(datatype)
                if (row["min"]):
                    if ('variable' not in i):
                        #first addition
                        i['variable'] = (str(row["min"] + '..' + str(row["max"])))
                    else:
                        i['variable'].append(str(row["min"] + '..' + str(row["max"])))
    print(inputList)
    return inputList

def parseOutputs(g, outputList):
    print("parseOutputs")

    # q = prepareQuery(
    #     'SELECT ?input ?properties ?dataRestrictions '
    #     'WHERE { ?command onem2m:hasInput ?input . 	?input onem2m:hasThingProperty ?properties . OPTIONAL {?input onem2m:hasDataRestriction_pattern ?dataRestrictions . } }',
    #     initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
    #     base = "http://yang-netconf-mqtt#")
    # result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
    #                             "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")
    #
    # for row in result:
    #     print(" %s %s %s " % row)
    #
    # _output = {}
    # _output['id'] = rawOutput[generic_id]
    #
    # tmp = getIDsfromContainer(rawOutput, oneM2M_hasThingProperties)
    # if len(tmp) > 0:
    #     _output['properties'] = tmp
    #
    # tmp = getOneM2MEntry(rawOutput, oneM2M_hasValue, returnList=True)
    # _output["returnType"] = custom_types[tmp[0][generic_type]]

    return outputList


def parseProperties(g, propList):
    print("parseProperties")
    # part 1 ThingProperty
    q = prepareQuery(
        'SELECT DISTINCT ?property ?type ?value '
        'WHERE { ?property rdf:type onem2m:ThingProperty . ?property rdf:type ?type. ?property onem2m:hasValue ?value . }',
        initNs = {"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
        base = "http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#",
                                "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"}, base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s %s " % row)
        if str(row["type"]) != "http://www.w3.org/2002/07/owl#NamedIndividual":
            prop = {}
            prop['id'] = str(row["property"])
            prop['type'] = str(row["type"])
            prop['values'] = [str(row["value"])]
            propList.append(prop)

    # part 2 YangDescription
    q = prepareQuery(
        'SELECT DISTINCT ?property ?type ?value '
        'WHERE { ?property rdf:type base:YangDescription. ?property rdf:type ?type. ?property onem2m:hasValue ?value. }',
            initNs={"base": "http://yang-netconf-mqtt#",
                    "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
            base="http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
            base="http://yang-netconf-mqtt#")

    for row in result:
        print(" %s %s %s " % row)
        if str(row["type"]) != "http://www.w3.org/2002/07/owl#NamedIndividual":
            prop = {}
            prop['id'] = str(row["property"])
            prop['type'] = str(row["type"])
            prop['values'] = [str(row["value"])]
            propList.append(prop)

    # part 3 OperationStateDescriptions hasDataRestriction_pattern
    q = prepareQuery(
        'SELECT DISTINCT  ?property ?type ?dataRestrictions ' 
        'WHERE { ?property rdf:type base:YangDescription. ?property rdf:type ?type. ?property onem2m:hasDataRestriction_pattern ?dataRestrictions. } ORDER BY ?dataRestrictions ',
            initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
            base="http://yang-netconf-mqtt#")
    result = g.query(q, initNs={"base": "http://yang-netconf-mqtt#", "onem2m": "http://www.onem2m.org/ontology/Base_Ontology/base_ontology#"},
            base="http://yang-netconf-mqtt#")

    dataRestriction = []
    for row in result:
        print(" %s %s %s " % row)
        if str(row["type"]) != "http://www.w3.org/2002/07/owl#NamedIndividual":
            prop = {}
            prop['id'] = str(row["property"])
            prop['type'] = str(row["type"])
            dataRestriction.append({'@value': str(row["dataRestrictions"])})
            prop['dataRestrictions'] = dataRestriction
            propList.append(prop)

    print(propList)
    return propList


#### END RDFLIB

#### START EXTERNAL FUNCTIONS
def generate_yang(json_str):
    global deviceList
    global serviceList
    global outDpList
    global ctrlfuncList
    global measurefuncList
    global opList
    global opStateList
    global cmdList
    global inputList
    global outputList
    global propList

    deviceList = []
    serviceList = []
    outDpList = []
    inDpList = []
    ctrlfuncList = []
    measurefuncList = []
    configfuncList = []
    autofuncList = []
    eventfuncList = []
    opList = []
    opStateList = []
    cmdList = []
    inputList = []
    outputList = []
    propList = []


    g = Graph()
    g.parse(data=json_str, format="json-ld", base="http://yang-netconf-mqtt#")

    parseDevices(g, deviceList)
    parseServices(g, serviceList)
    parseOutDps(g, outDpList)
    parseInDps(g, inDpList)
    parseCtrlFunctionality(g, ctrlfuncList)
    parseMeasureFunctionality(g, measurefuncList)
    parseConfigFunctionality(g, configfuncList)
    parseAutomationFunctionality(g, autofuncList)
    parseEventFunctionality(g, eventfuncList)
    parseOpStates(g, opStateList)
    parseOperations(g,opList)
    parseCommands(g, cmdList)
    parseInputs(g, inputList)
    parseOutputs(g, outputList)
    parseProperties(g, propList)

    # parse everything into objects
    #data = json.loads(json_str)



    # create References
    for i in inputList:
        createReferences(i['properties'], propList)
    for i in outputList:
        createReferences(i['properties'], propList)

    for i in opStateList:
        createReferences(i['properties'], propList)

    for i in cmdList:
        createReferences(i['inputs'], inputList)
        # createReferences(i['outputs'], outputList)

    for i in opList:
        createReferences(i['inputs'], inputList)
        createReferences(i['commands'], cmdList)
        createReferences(i['operationState'], opStateList)
        #if 'inDps' in opList:
            #createReferences(i['inDps'], inDpList)

    for i in measurefuncList:
        createReferences(i['properties'], propList)

    for i in ctrlfuncList:
        createReferences(i['commands'], cmdList)
        createReferences(i['properties'], propList)

    for i in eventfuncList:
        createReferences(i['properties'], propList)

    for i in configfuncList:
        createReferences(i['commands'], cmdList)
        createReferences(i['properties'], propList)

    for i in autofuncList:
        createReferences(i['commands'], cmdList)
        createReferences(i['properties'], propList)

    for i in serviceList:
        if 'functionalities' in i:
            createReferences(i['functionalities'], ctrlfuncList)
            createReferences(i['functionalities'], measurefuncList)
            createReferences(i['functionalities'], configfuncList)
            createReferences(i['functionalities'], autofuncList)
            createReferences(i['functionalities'], eventfuncList)
        if 'operations' in i:
            createReferences(i['operations'], opList)
        if 'subservices' in i:
            createReferences(i['subservices'], serviceList)
        if 'outDps' in i:
            createReferences(i['outDps'], outDpList)

    for i in deviceList:
        createReferences(i['services'], serviceList)
        createReferences(i['functionalities'], ctrlfuncList)
        createReferences(i['functionalities'], measurefuncList)
        createReferences(i['functionalities'], configfuncList)
        createReferences(i['functionalities'], autofuncList)
        createReferences(i['functionalities'], eventfuncList)
        createReferences(i['properties'], propList)

    # DONE PARSING ONEM2M
    # START GENERATING YANG

    yangdata = []
    generateYang(deviceList, yangdata) #serviceList

    stream = StringIO()

    # gets filled with all availabe pyang output format plugins
    PYANG_PLUGINS = {}

    # register and initialise pyang plugin
    pyang.plugin.init([])
    for plugin in pyang.plugin.plugins:
        plugin.add_output_format(PYANG_PLUGINS)
    del plugin

    plugin = PYANG_PLUGINS['yang']

    optparser = OptionParser()
    plugin.add_opts(optparser)

    # pyang plugins also need a pyang.Context
    ctx = pyang.Context(DummyRepository())

    # which offers plugin-specific options (just take defaults)
    ctx.opts = optparser.parse_args([])[0]

    # ready to serialize
    plugin.emit(ctx, yangdata, stream)

    # and return the resulting data
    stream.seek(0)
    yang = stream.getvalue()

    # generate mqtt_command_mapping
    mqtt_commands = {}
    for func in ctrlfuncList:
        ID = func['id'].split("#")[1]  # check if full URI is working too
        cmd = func['commands'][0]
        for op in opList:
            if cmd in op['commands']:
                mqtt_commands[ID] = (op['mqttMethod'][generic_value], op['mqttTopic'][generic_value], op['inputs'])
    for func in autofuncList:
        ID = func['id'].split("#")[1]  # check if full URI is working too
        cmd = func['commands'][0]
        for op in opList:
            if cmd in op['commands']:
                mqtt_commands[ID] = (op['mqttMethod'][generic_value], op['mqttTopic'][generic_value], op['inputs'])
    for func in configfuncList:
        ID = func['id'].split("#")[1]  # check if full URI is working too
        cmd = func['commands'][0]
        for op in opList:
            if cmd in op['commands']:
                mqtt_commands[ID] = (op['mqttMethod'][generic_value], op['mqttTopic'][generic_value], op['inputs'])

    # generate uuid set
    uuid_set = set()
    for dev in deviceList:
        uuid = getValueFromID(dev['properties'], custom_deviceUUID)
        uuid_set.add(uuid)

    device_category = getValueFromID(deviceList[0]['properties'], custom_deviceCategory)
    return (yang, mqtt_commands, uuid_set, device_category, deviceList, ctrlfuncList, opList)


def delete_yang_module(device_list, ctrl_func_list, op_list):
    # generate yang model again

    yangdata = []
    try:
        generateYang(device_list, yangdata) # servicelist
    except Exception as err:
        track = traceback.format_exc()
        print(track)
    stream = StringIO()

    # gets filled with all availabe pyang output format plugins
    PYANG_PLUGINS = {}

    # register and initialise pyang plugin
    pyang.plugin.init([])
    for plugin in pyang.plugin.plugins:
        plugin.add_output_format(PYANG_PLUGINS)
    del plugin

    plugin = PYANG_PLUGINS['yang']

    optparser = OptionParser()
    plugin.add_opts(optparser)

    # pyang plugins also need a pyang.Context
    ctx = pyang.Context(DummyRepository())

    # which offers plugin-specific options (just take defaults)
    ctx.opts = optparser.parse_args([])[0]

    # ready to serialize
    plugin.emit(ctx, yangdata, stream)

    # and return the resulting data
    stream.seek(0)
    yang = stream.getvalue()

    # generate mqtt_command_mapping
    mqtt_commands = {}
    for func in ctrl_func_list:
        ID = func['id'].split("#")[1]  # check if full URI is working too
        cmd = func['commands'][0]
        for op in op_list:
            if cmd in op['commands']:
                mqtt_commands[ID] = (op['mqttMethod'][generic_value], op['mqttTopic'][generic_value], op['inputs'])

    return (yang, mqtt_commands)

if __name__ == "__main__":
    uuid_set = set()
    start = time.time()

    with open('ontology/bright_motion_led-rgb.owl') as data_file:
    #with open('ontology/mqtt-cap-json-v5-2-json-ld.owl') as data_file:
        yang, mqtt_commands, uuid_set, device_category, deviceList, ctrlfuncList, opList = generate_yang(data_file.read())
        print(yang)

    end = time.time()
    print(end - start)