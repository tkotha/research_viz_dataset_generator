import os
import os.path
from os.path import *
import sys
import math
import pprint
import json
from helper import *

#the batches list is a list of pairs of paths and default argfiles (if specified, otherwise empty string)

'''
	batches: [
			{path: "path/to/experimetn/folder/1", argfile:"testargfile.args"},
			#etc...
	]

'''

#we also need to expand the file arg system to also handle reeb graph interactions

# (any and all reeb graphs made will be auto-generating a corresponding cp_pair file as well)
def parseBargFile(bargfile, path):
	fileargs = {"barg-file" : "",
				"path":"",
				"batches" : [],
				"validation-error" : False,
				"error-reason" : "",
		}

	currentArgGroup = "batches"
	ArgGroupDelimiter = ":::"
	PairingDelimiter = "::"
	fileargs["barg-file"] = bargfile
	fileargs["path"] = path
	def parseArgs(textline, argGroup = ""):
		if argGroup == "":
			#we do nothing in the empty arg group
			return
		elif argGroup == "batches":
			args = textline.strip().split()
			parsed_args = dict()
			for a in args:
				keyvalue = a.split(PairingDelimiter)
				keyvalue[0] = keyvalue[0].strip()
				keyvalue[1] = keyvalue[1].strip()
				if keyvalue[0] == "path":
					#now we must verify that the path for the argfile exists
					checkpath = determineAbsOrRelativePath(keyvalue[1], path)
					#we are assuming here that we are only verifying folders
					if os.path.isdir(checkpath):
						# print("path verified")
						parsed_args["path"] = keyvalue[1]
					else:
						fileargs["validation-error"] = True
						fileargs["error-reason"] = "error in "+bargfile+", path does not exist: "+keyvalue[1]+"! QUIT"
						return
				elif keyvalue[0] == "arg-file":
					#dont worry about verifying the arg-file here, we'll have our chance later on to do so
					parsed_args["arg-file"] = keyvalue[1]
			if "arg-file" not in parsed_args.keys():
				parsed_args["arg-file"] = ""
			fileargs["batches"].append(parsed_args)
		else:
			fileargs["error-reason"]=("error in "+bargfile+", unrecognized arg group: "+ argGroup+"! QUIT")
			fileargs["validation-error"] = True
			return
	def validationCheck():
		pass
	with open(os.path.join(path,bargfile),'r') as f:
		for line in f:
			if fileargs["validation-error"]:
				#we assume that the error reason has been set already
				return fileargs
			textline = line.strip()
			if textline.startswith("//"):
				continue
			if textline is "":
				continue
			if textline.endswith(ArgGroupDelimiter):
				currentArgGroup = textline[:-len(ArgGroupDelimiter)]
			else:
				parseArgs(textline, currentArgGroup)
	validationCheck()

	return fileargs