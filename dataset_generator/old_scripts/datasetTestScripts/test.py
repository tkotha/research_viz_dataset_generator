import os
import sys
import math
import pprint
import json
from helper import *

#...what should I do in the event the argfile is in a completely separate path?
#   should that count as an error?
#   would this logic apply to batch files? or do they need separate consideration?
cmdargs = {"argFile" : "",
		   "path" : os.getcwd()}
def resetCmdArgs():
	cmdargs["argFile"] = ""
	cmdargs["path"] = os.getcwd()
def parseCmdArgs(args):
	for i in range(0,len(args)):
		s = args[i]
		if s == "":
			continue
		parts = s.split(':')
		if len(parts) != 2:
			print("error, invalid arg "+s)
			exit()
		parts[0].strip()
		parts[1].strip()
		if parts[0] not in cmdargs:
			print("error, unrecognized argument " + parts[0])
		else:
			if parts[0] == "path":
				#process path
				if os.path.isabs(parts[1]):
					cmdargs[parts[0]] = parts[1]
				else:
					cmdargs[parts[0]] = os.path.join(cmdargs[parts[0]], parts[1])
					if not os.path.exists(cmdargs[parts[0]]):
						print("error, the specified path \""+parts[1]+"\" does not exist! Abort experiment!")
						exit()
			else:
				cmdargs[parts[0]] = parts[1]


fileargs = {"modelObj" : "",
			"modelConn": "",
			"modelGeo" : "",
			"emptyFuncCount" : 0,
			"funcFiles": [],
			"noiseParams" : {"amplitude" : 0.0},
			"gauss2dParams" : { "amplitude": 0.0,
						 		"stddev": [0.0,0.0],
						 		"pos": [0.0,0.0]},
			"gauss3dParams" : { "amplitude": 0.0,
						 		"stddev": [0.0, 0.0, 0.0],
						 		"pos": [0.0, 0.0, 0.0]},
			"validationError" : False,
			"errorReason" : "",
			"useNoise" : False,
			"useGauss2d": False,
			"useGauss3d": False
		}
def resetFileArgs():
	fileargs["modelObj"] = ""
	fileargs["modelConn"] = ""
	fileargs["modelGeo"] = ""
	fileargs["emptyFuncCount"] = 0
	fileargs["funcFiles"] = []
	
	fileargs["noiseParams"]["amplitude"] = 0.0

	fileargs["gauss2dParams"]["amplitude"] = 0.0
	fileargs["gauss2dParams"]["stddev"] = [0.0,0.0,0.0]
	fileargs["gauss2dParams"]["pos"] = [0.0,0.0,0.0]

	fileargs["gauss3dParams"]["amplitude"] = 0.0
	fileargs["gauss3dParams"]["stddev"] = [0.0,0.0,0.0]
	fileargs["gauss3dParams"]["pos"] = [0.0,0.0,0.0]

	fileargs["validationError"] = False
	fileargs["errorReason"] = ""
	fileargs["useNoise"] = False
	fileargs["useGauss3d"] = False
	fileargs["useGauss2d"] = False
# we assume a valid argfile here
def parseFileArgs(argfile, path):
	currentArgGroup = ""
	ArgGroupDelimiter = "::"
	#used when dealing with func parameters, ie the argname:: lines
	#by default, we start at the top level, which is empty
	def parseArgs(textline, argGroup =""):
		parts = textline.strip().split(':')
		#print(parts)
		if len(parts) == 1 and parts[0] == '':
			return
		elif len(parts) == 1:
			parts[0] = parts[0].strip()
		elif len(parts) == 2:
			parts[0] = parts[0].strip()
			parts[1] = parts[1].strip()
		if len(parts) != 2 and argGroup not in  ["funcFiles"]:
			fileargs["errorReason"]=("error in "+argfile+", file arg \""+textline+"\" does not follow the form of argname: value! QUIT")
			fileargs["validationError"] = True
			return
		#now we handle each part case by case
		#work on a substructure in the current dictionary
		#keep in mind, some arg groups have specific functions, so you'll have to case split here
		if argGroup == "":
			#here we set all top level arguments
			if parts[0] == "modelObj":
				if os.path.isfile(os.path.join(path, parts[1])) and getExtensionText(parts[1]) == "obj":
					fileargs["modelObj"] = parts[1]
				else:
					fileargs["errorReason"]=("error in "+argfile+", invalid OBJ model: "+parts[1]+" file! QUIT")
					fileargs["validationError"] = True
					return

			elif parts[0] == "modelConn":
				if os.path.isfile(os.path.join(path, parts[1]))and getExtensionText(parts[1]) == "txt":
					fileargs["modelConn"] = parts[1]
				else:
					fileargs["errorReason"]=("error in "+argfile+", invalid CONN model file! QUIT")
					fileargs["validationError"] = True
					return

			elif parts[0] == "modelGeo":
				if os.path.isfile(os.path.join(path, parts[1])) and getExtensionText(parts[1]) == "txt":
					fileargs["modelGeo"] = parts[1]
				else:
					fileargs["errorReason"]=("error in "+argfile+", invalid GEO model file! QUIT")
					fileargs["validationError"] = True
					return

			elif parts[0] == "emptyFuncCount":
				fileargs["emptyFuncCount"] = int(parts[1])
			else:
				fileargs["errorReason"]=("error in "+argfile+", unrecognized top level command: "+parts[1]+"! QUIT")
				fileargs["validationError"] = True
				return

		elif argGroup == "funcFiles":
			#first validate the file path
			if os.path.isfile(os.path.join(path, parts[0])):
				fileargs["funcFiles"].append(parts[0])
			else:
				fileargs["errorReason"]=("error in "+argfile+", function file "+parts[0]+" does not exist in directory! QUIT")
				fileargs["validationError"] = True
				return

		elif argGroup == "noiseParams":
			if parts[0] == "amplitude":
				fileargs["noiseParams"]["amplitude"] = float(parts[1])
			else:
				fileargs["errorReason"]=("error in "+argfile+", unrecognized noise parameter "+parts[1]+"! QUIT")
				fileargs["validationError"] = True
				return

		elif argGroup == "gauss2dParams":
			if parts[0] == "amplitude":
				fileargs["gauss2dParams"]["amplitude"] = float(parts[1])
			elif parts[0] == "stddev":
				vec = parseFloatVector(parts[1])
				if len(vec) != 2:
					fileargs["errorReason"]=("error in gauss2d args, expected stddev vec is not of size 2! QUIT")
					fileargs["validationError"] = True
					return
				fileargs["gauss2dParams"]["stddev"] = vec
			elif parts[0] == "pos":
				vec = parseFloatVector(parts[1])
				if len(vec) != 2:
					fileargs["errorReason"]=("error in gauss2d args, expected pos vec is not of size 2! QUIT")
					fileargs["validationError"] = True
					return
				fileargs["gauss2dParams"]["pos"] = vec
			else:
				fileargs["errorReason"]=("error in "+argfile+", unrecognized noise parameter "+parts[1]+"! QUIT")
				fileargs["validationError"] = True
				return

		elif argGroup == "gauss3dParams":
			if parts[0] == "amplitude":
				fileargs["gauss3dParams"]["amplitude"] = float(parts[1])
			elif parts[0] == "stddev":
				vec = parseFloatVector(parts[1])
				if len(vec) != 3:
					fileargs["errorReason"]=("error in gauss3d args, expected stddev vec is not of size 3! QUIT")
					fileargs["validationError"] = True
					return
				fileargs["gauss3dParams"]["stddev"] = vec
			elif parts[0] == "pos":
				vec = parseFloatVector(parts[1])
				if len(vec) != 3:
					fileargs["errorReason"]=("error in gauss3d args, expected pos vec is not of size 3! QUIT")
					fileargs["validationError"] = True
					return
				fileargs["gauss3dParams"]["pos"] = vec
			else:
				fileargs["errorReason"]=("error in "+argfile+", unrecognized noise parameter "+parts[1]+"! QUIT")
				fileargs["validationError"] = True
				return
		else:
			fileargs["errorReason"]=("error in "+argfile+", unrecognized arg group: "+ argGroup+"! QUIT")
			fileargs["validationError"] = True
			return

	#all validation checks occur here!
	def validationCheck():
		if fileargs["modelObj"] != "" and (fileargs["modelConn"] != "" or fileargs["modelGeo"] != ""):
			fileargs["errorReason"] = "error in "+argfile+", cannot have both OBJ and CONN/GEO models defined! QUIT"
			fileargs["validationError"] = True
			return
		elif fileargs["modelObj"] == "" and not (fileargs["modelConn"] != "" and fileargs["modelGeo"] != ""):
			fileargs["errorReason"] = "error in "+argfile+", if OBJ is not being used, CONN and GEO files must be defined! QUIT"
			fileargs["validationError"] = True
			return
		elif fileargs["modelConn"] == fileargs["modelGeo"]:
			fileargs["errorReason"] = "error in "+argfile+", CONN and GEO cannot use the same file, they need different data! QUIT"
			fileargs["validationError"] = True
			return

	with open(os.path.join(path, argfile), 'r') as f:
		for line in f:
			if fileargs["validationError"]:
				print(fileargs["errorReason"])
				return
			textline = line.strip()
			if textline.startswith("//"): #tis a comment line
				continue
			if textline.endswith(ArgGroupDelimiter):
				#toggle the current arg group
				currentArgGroup = textline[:-2]
				if currentArgGroup == "noiseParams":
					fileargs["useNoise"] = True
				elif currentArgGroup == "gauss2dParams":
					fileargs["useGauss2d"] = True
				elif currentArgGroup == "gauss3dParams":
					fileargs["useGauss3d"] = True
			else:
				parseArgs(textline, currentArgGroup)
	validationCheck()



#we assume a valid cmd string here
def prepareExperiment(args):
	parseCmdArgs(args)
	path = cmdargs["path"]
	target_argfile = cmdargs["argFile"]


	#file extension masking test
	files = getFiles(path, "args")
	print(files)

	# #now for the argfile cases
	target_argfile = argFileValidity(files, target_argfile)

	# print(target_argfile)

	#now to parse the arg file
	parseFileArgs(target_argfile, path)
	print("EXPERIMENT FOR: "+target_argfile)
	print(json.dumps(fileargs, indent=4))


if __name__ == "__main__":
	prepareExperiment(sys.argv[1:])