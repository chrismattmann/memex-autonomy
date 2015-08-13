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
from os import listdir
from os.path import join, isfile, exists

_verbose = False
_helpMessage = '''

Usage: khooshe_output.py [-d <dir of JSON files with Tika locations>] [-o <output directory for sample_pts.csv>]

Operation:

-o --outdir
    Output directory for sample_pts.csv to feed into Khooshe.
-d --dir
    The directory of JSON files with Tika Locations.
-v --verbose
    Work verbosely.
'''

def generateGeoCsv(dirpath, outdirpath):
    outfile = "sample_points.csv"
    onlyfiles = [ f for f in listdir(dirpath) if isfile(join(dirpath,f)) ]
    print "[INFO] Read "+str(len(onlyfiles))+" json files from ["+dirpath+"]"

    if not os.path.exists(outdirpath):
        print "[INFO] Creating ["+outdirpath+"]"
        os.makedirs(outdirpath)

    outfilename = os.path.join(outdirpath, outfile)
    print "[INFO] Creating ["+outfilename+"]"

    numPoints = 0
    with open(outfilename, 'w') as of:
        for f in onlyfiles:
            filename = os.path.join(dirpath, f)
            outfilename = os.path.join(outdirpath, outfile)
            with open(filename, 'r') as fd:
                jsonDoc = json.load(fd)
                if "tika_location" in jsonDoc:
                    tikaLoc = jsonDoc["tika_location"]
                    geoLat = None
                    geoLng = None
                    if "geo_lat" in tikaLoc:
                        geoLng = tikaLoc["geo_lat"] #workaround, flipped
                    if "geo_lng" in tikaLoc:
                        geoLat = tikaLoc["geo_lng"] #workaround, flipped

                    if geoLat != None and geoLng != None:
                        verboseLog("Writing pt: ("+geoLng+","+geoLat+") from JSON: ["+filename+"]")
                        of.write(geoLng+","+geoLat+"\n")
                        numPoints += 1


        print "[INFO] Khooshe Output complete: generated "+str(numPoints)+" points."

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
          opts, args = getopt.getopt(argv[1:],'hvd:o:',['help', 'verbose', 'dir=', 'outdir='])
       except getopt.error, msg:
         raise _Usage(msg)    
     
       if len(opts) == 0:
           raise _Usage(_helpMessage)

       dir=None
       outdir=None
       
       for option, value in opts:           
          if option in ('-h', '--help'):
             raise _Usage(_helpMessage)
          elif option in ('-v', '--verbose'):
             global _verbose
             _verbose = True
          elif option in ('-o', '--outdir'):
              outdir = value
          elif option in ('-d', '--dir'):
              dir = value

       if dir == None or outdir == None:
           raise _Usage(_helpMessage)

       generateGeoCsv(dir, outdir)

   except _Usage, err:
       print >>sys.stderr, sys.argv[0].split('/')[-1] + ': ' + str(err.msg)
       return 2

if __name__ == "__main__":
   sys.exit(main())
