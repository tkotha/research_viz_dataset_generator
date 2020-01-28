import os
import sys
import json
import math
from helper import *
from test import *

batchargs = {   "argFile" : "",
				"path" : os.getcwd(),
				"batches": [],
				"validationError": False,
				"errorReason": ""}

def parseBatchCmdArgs(args):
	for i in range(0, len(args)):
		s = args[i]
		if s == "":
			continue
		parts = s.split(':')
		if len(parts) != 2:
			print("error, invalid arg "+s)
			exit()
		parts[0].strip()
		parts[1].strip()
		if parts[0] not in batchargs:
			print("error, unrecognized argument "+parts[0])
		else:
			if parts[0] == "path":
				#process path
				if os.path.isabs(parts[1]):
					batchargs[parts[0]] = parts[1]
				else:
					batchargs[parts[0]] = os.path.join(batchargs[parts[0]], parts[1])
					if not os.path.exists(batchargs[parts[0]]):
						print("error, the specified path \""+parts[1]+"\" does not exist! Abort Batch!")
						exit()
			else:
				batchargs[parts[0]] = parts[1]

def parseBatchFileArgs(argFile, path):
	currentArgGroup = ""
	ArgGroupDelimiter = "::"

	def parseArgs(textline, argGroup = ""):
		if argGroup == "":
			return
		elif argGroup == "batches":
			batchargs["batches"].append(textline.strip().split(' '))
		else:
			batchargs["errorReason"]=("error in "+argFile+", unrecognized arg group: "+ argGroup+"! QUIT")
			batchargs["validationError"] = True
			return
	def validationCheck():
		pass

	with open(os.path.join(path, argFile), 'r') as f:
		for line in f:
			if batchargs["validationError"]:
				print(batchargs["errorReason"])
				return
			textline = line.strip()
			if textline.startswith("//"):
				continue
			if textline.endswith(ArgGroupDelimiter):
				currentArgGroup = textline[:-2]
			else:
				parseArgs(textline, currentArgGroup)
	validationCheck()

if __name__ == "__main__":
	numcount = getDirCount(os.getcwd())
	print(numcount)
	parseBatchCmdArgs(sys.argv[1:])
	path = batchargs["path"]
	target_argfile = batchargs["argFile"]

	files = getFiles(path, "bargs")
	print(files)

	#now for the argfile cases
	target_argfile = argFileValidity(files, target_argfile)
	parseBatchFileArgs(target_argfile, path)
	print(json.dumps(batchargs, indent=4))

	for i,e in enumerate(batchargs["batches"]):
		resetFileArgs()
		resetCmdArgs()
		prepareExperiment(e)
