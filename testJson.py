#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# ----------------------------------------------------------------------------
# pythonSerialMonitor.py.py
# used by EVSE-Serial-Debug-Monitor.py
# Copyright 2020 brainelectronics
# All rights reserved.
#

import json

def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)

    return out

def main():
    with open("dummyData.json") as json_file:
        data = json.load(json_file)
        prettyJsonDump = json.dumps(data, indent=4)
        print(prettyJsonDump)
        print(data)
        print(type(data))

        flatJson = flatten_json(data)
        prettyFlatJson = json.dumps(flatJson, indent=4)
        print(prettyFlatJson)
        print(flatJson)
        print(type(flatJson))

        for ele in flatJson:
            print("key: %s, val: %s" %(ele, flatJson[ele]))

if __name__ == '__main__':
    main()
