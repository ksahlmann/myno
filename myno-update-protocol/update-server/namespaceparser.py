import xml.etree.ElementTree as ET

def find(xml, path1, path2):
	return xml.find(str(path1+"{urn:ietf:params:xml:ns:yang:yin:1}"+path2))

def findall(xml, path1, path2):
	return xml.findall(str(path1+"{urn:ietf:params:xml:ns:yang:yin:1}"+path2))
	
