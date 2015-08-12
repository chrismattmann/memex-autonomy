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

import hashlib
import os
import sys
import getopt
from os import listdir
from os.path import isfile, join

_verbose = False
_helpMessage = '''

Usage: dedup.py [-d <dir of files>] [-c]

Operation:

-c --commit
    Don't just print which dupes to remove, actually delete them.
-d --dir
    The directory of files to perform MD5 hashing on and to dedup.
-v --verbose
    Work verbosely.
'''

def dedup(dirpath, commit):
    hashes = {}
    numdupes = 0
    numfiles = 0
    numremoved = 0
    onlyfiles = [ f for f in listdir(dirpath) if isfile(join(dirpath,f)) ]
    for f in onlyfiles:
        filename = os.path.join(dirpath, f)
        hash = hashlib.md5(open(filename, 'rb').read()).digest()
        if hash in hashes:
            verboseLog("[INFO] Dupe found: ["+filename+"]")
            if commit:
                verboseLog("[INFO] Removing: ["+filename+"]")
                os.remove(filename)
                numremoved += 1
            numdupes += 1
        else:    
            hashes[hash] = f
        numfiles += 1

    print "Discovered "+str(len(hashes.keys()))+" unique hashes."
    print "Discovered "+str(numdupes)+" duplicate files."
    print "Removed: "+str(numremoved)+" files."
    print "Total "+str(numfiles)+" files."

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
          opts, args = getopt.getopt(argv[1:],'hvd:c',['help', 'verbose', 'dir=', 'commit'])
       except getopt.error, msg:
         raise _Usage(msg)    
     
       if len(opts) == 0:
           raise _Usage(_helpMessage)

       dir=None
       commit=False
       
       for option, value in opts:           
          if option in ('-h', '--help'):
             raise _Usage(_helpMessage)
          elif option in ('-v', '--verbose'):
             global _verbose
             _verbose = True
          elif option in ('-c', '--commit'):
              commit = True
          elif option in ('-d', '--dir'):
              dir = value

       if dir == None:
           raise _Usage(_helpMessage)

       dedup(dir, commit)

   except _Usage, err:
       print >>sys.stderr, sys.argv[0].split('/')[-1] + ': ' + str(err.msg)
       return 2

if __name__ == "__main__":
   sys.exit(main())
