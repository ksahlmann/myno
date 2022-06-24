#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@author: kristina.sahlmann
"""

class SensorAggregat:
    def __init__(self, topic):
        self.topic = topic
        self.counter = 0
        self.avg = 0

    def getAvg(self, new_value):

        #reset counter and avg after 5 values
        if(self.counter == 5):
            self.counter = 0
            self.avg = 0

        #( Counter * AVG + NW ) / Counter + 1
        if(self.avg == 0):
            avg = new_value
        result = round((self.counter * self.avg + float(new_value)) / (self.counter + 1), 2)
        self.counter += 1
        self.avg = result
        return result
