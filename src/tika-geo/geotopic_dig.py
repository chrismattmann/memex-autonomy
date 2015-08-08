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

import json
import os
import sys
import getopt
import glob
from tika.tika import callServer
from tika.tika import ServerEndpoint
from elasticsearch import Elasticsearch
from elasticsearch import helpers

_verbose = False
_helpMessage = '''

Usage: geotopic_dig.py [-e <elastic search url>] [-i <index name>] [-o <output dir>] [-s <search index name>] [-g <geo field name>] [-m <match query JSON>] [-d <id field>]

Operation:

-e --esUrl
    The URL to the Elasticsearch server to contact. Defaults to http://localhost:9200.
-s --search
    The Elasticsearch index to search, e.g., dig-autonomy-18.
-i --index
    The Elasticsearch index, e.g., dig-autonomy-18-geo, to index to.
-o --outdir
    Skip indexing to Elasticsearch and just write the JSON docs in this directory to index later.
-g --geoField
    The name of the geoField from the ES documents to use as input to Tika's GeoTopicParser. Defaults to 'text'.
-m --match
    The match query to use (if Elasticsearch) to select documents.
-d --idField
    The JSON document field to use to determine whether this document has been already indexed and/or written to outdir.
-v --verbose
    Work verbosely.
'''

def readIds(identifier, outDir):
    verboseLog("Reading IDs from ["+outDir+"*.json]")
    ids = {}
    jsonFiles = glob.glob(outDir + "*.json")
    for f in jsonFiles:
        with open(f, 'r') as fd:
            doc = json.load(fd)
            val = getField(identifier, doc)
            if val != None:
                verboseLog("Adding id: ["+val+"]")
                ids[val] = True

    verboseLog("Read ["+str(len(ids.keys()))+"] ids.")

    return ids

def getField(field, doc):
    if "." in field:
        toks = field.rsplit('.')
        dict = doc
        for t in toks:
            if not t in dict:
                return None
            dict = dict[t]
        return dict
    else:
        if not field in doc:
            return None
        else:
            return doc[field]
            

def tikaGeoExtract(esHit, geoField):
    text = getField(geoField, esHit['_source'])
    if text == None: return None
    res = callServer('put', ServerEndpoint, '/rmeta', text, {'Accept' : 'application/json', 'Content-Type' : 'application/geotopic'}, False)
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
        
            
def geoIndex(search, index, outDir, esUrl, geoField, match, ids, idField):
    verboseLog("Connecting to Elasticsearch: ["+esUrl+"]: geoField: ["+geoField+"]: search index: ["+search+"]: match: ["+match+"]: idField: ["+idField+"]")
    es = Elasticsearch([esUrl])
    count = 0
    if not os.path.exists(outDir):
        verboseLog("Creating ["+outDir+"] since it doesn't exist.")
        os.makedirs(outDir)
    else:
        count = len([name for name in os.listdir(outDir) if os.path.isfile(os.path.join(outDir, name))])
        verboseLog(str(count)+" existing files in ["+outDir+"]")
        count = count + 1

    query = {"query": {"match": eval(match)}}
    res = helpers.scan(client= es, query=query, scroll= "120m", index=search, raise_on_error=False, timeout="120m")
    docs = []
    tikaGeoCount = 0

    for hit in res:        
        newDoc = hit['_source']
        idVal = getField(idField, newDoc)
        if idVal != None and idVal in ids:
            verboseLog("Skipping Tika GeoTopic analysis on doc: ["+idVal+"] doc already generated.")
            continue

        tikaJson = tikaGeoExtract(hit, geoField)
        addTikaGeo(tikaJson, newDoc)
        hasTikaGeo = "no"
        if "tika_location" in newDoc:
            hasTikaGeo = "yes"
            tikaGeoCount = tikaGeoCount + 1

        count = count + 1
        if index != None:
            es.index(index=index, doc_type='article', body=newDoc)
            print "Indexing "+newDoc["uri"]+" Tika Geo: ["+hasTikaGeo+"]: Total Docs Indexed: ["+str(count)+"]"

        if outDir != None:
            filePath = outDir + str(count)+".json"
            with open(filePath, "w") as outFile:
                outFile.write(json.dumps(newDoc))
            print "Writing ["+filePath+"] Tika Geo: ["+hasTikaGeo+"]: Total Docs Written: ["+str(count)+"]"

        ids[idVal] = True
        
    if index != None:
        es.indices.refresh(index=index)

    print "Total Docs Indexed: ["+str(count)+"]"
    print "Total Docs with Tika Geo: ["+str(tikaGeoCount)+"]"

def verboseLog(message):
    if _verbose:
        print >>sys.stderr, message

class _Usage(Exception):
    '''An error for problems with arguments on the command line.'''
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
   if argv is None:
     argv = sys.argv

   try:
       try:
          opts, args = getopt.getopt(argv[1:],'hve:s:i:o:g:m:d:',['help', 'verbose', 'esUrl=', 'search=', 'index=', 'outdir=', 'geoField=', 'match=', 'idField='])
       except getopt.error, msg:
         raise _Usage(msg)    
     
       if len(opts) == 0:
           raise _Usage(_helpMessage)

       index=None
       search=None
       outDir=None
       esUrl=None
       geoField=None
       match=None
       idField=None
       ids = None
       
       for option, value in opts:           
          if option in ('-h', '--help'):
             raise _Usage(_helpMessage)
          elif option in ('-v', '--verbose'):
             global _verbose
             _verbose = True
          elif option in ('-i', '--index'):
              index = value
          elif option in ('-s', '--search'):
              search = value
          elif option in ('-o', '--outdir'):
              outDir = value
              if outDir[len(outDir)-1] != "/":
                  outDir += "/"
          elif option in ('-e', '--esUrl'):
              esUrl = value
          elif option in ('-g', '--geoField'):
              geoField = value
          elif option in ('-m', '--match'):
              match = value
          elif option in ('-d', '--idField'):
              idField = value

       if search == None or (index == None and outDir == None) or (index != None and outDir != None):
           raise _Usage(_helpMessage)

       if idField != None:
           ids = readIds(idField, outDir)

       if esUrl == None:
           esUrl = "http://localhost:9200"
       
       if geoField == None:
           geoField = "text"

       if match == None:
           match = "{ '_type' : 'article' }"

       geoIndex(search, index, outDir, esUrl, geoField, match, ids, idField)

   except _Usage, err:
       print >>sys.stderr, sys.argv[0].split('/')[-1] + ': ' + str(err.msg)
       return 2

if __name__ == "__main__":
   sys.exit(main())
