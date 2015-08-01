#!/usr/bin/env python2.7
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 

from tika.tika import callServer
from tika.tika import ServerEndpoint
import json
from elasticsearch import Elasticsearch
from elasticsearch import helpers

def tikaGeoExtract(esHit):
    if not "text" in esHit['_source']: return None
    res = callServer('put', ServerEndpoint, '/rmeta', esHit['_source']['text'], {'Accept' : 'application/json', 'Content-Type' : 'application/geotopic'}, False)
    if res[0] != 200:
        return None
    jsonParse = json.loads(res[1])
    return jsonParse[0]

def addTikaGeo(tJson, nJson):
    if tJson == None: return
    tikaGeo = {}
    numOptionalLocs = 0
    for key in tJson.keys():
        if key == "Geographic_NAME":
            tikaGeo["geo_name"] = tJson[key]
        if key == "Geographic_LATITUDE":
            tikaGeo["geo_lat"] = tJson[key]
        if key == "Geographic_LONGITUDE":
            tikaGeo["geo_lng"] = tJson[key]

        if "Optional_NAME" in key:
            num = int(key[len(key)-1])
            if num > numOptionalLocs:
                numOptionalLocs = num

    tikaOptLocs = []
    for i in range(1, numOptionalLocs):
        tikaOptLoc = {}
        tikaOptLoc["alt_geo_name"] = tJson["Optional_NAME"+str(i)]
        tikaOptLoc["alt_geo_lat"] = tJson["Optional_LATITUDE"+str(i)]
        tikaOptLoc["alt_geo_lng"] = tJson["Optional_LONGITUDE"+str(i)]
        tikaOptLocs.append(tikaOptLoc)
        
    if len(tikaOptLocs) > 0:
        tikaGeo["alternate_locations"] = tikaOptLocs
    
    if len(tikaGeo.keys()) > 0:
        nJson["tika_location"] = tikaGeo
        
            

es = Elasticsearch()
query = {"query": {"match": {'_type':'article'}}}
res = helpers.scan(client= es, query=query, scroll= "10m", index="dig-autonomy-18", doc_type="article", timeout="10m")
docs = []
count = 0
tikaGeoCount = 0

for hit in res:
    tikaJson = tikaGeoExtract(hit)
    newDoc = hit['_source']
    addTikaGeo(tikaJson, newDoc)
    hasTikaGeo = "no"
    if "tika_location" in newDoc:
        hasTikaGeo = "yes"
        tikaGeoCount = tikaGeoCount + 1

        es.index(index='dig-autonomy-18-geo', doc_type='article', body=newDoc)
    count = count + 1
    print "Indexing "+newDoc["uri"]+" Tika Geo: ["+hasTikaGeo+"]: Total Docs Indexed: ["+str(count)+"]"


es.indices.refresh(index='dig-autonomy-18-geo')
print "Total Docs Indexed: ["+str(count)+"]"
print "Total Docs with Tika Geo: ["+str(tikaGeoCount)+"]"
