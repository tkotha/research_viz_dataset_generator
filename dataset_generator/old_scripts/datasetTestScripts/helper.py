import os
import sys
import math
import json

#https://stackoverflow.com/questions/541390/extracting-extension-from-filename-in-python
def getExtensionText(filename):
	return os.path.splitext(filename)[1][1:]

#https://stackoverflow.com/questions/3883138/how-do-i-read-the-number-of-files-in-a-folder-using-python
def getFileCount(path, extensionTextMask = ""):
	return len(getFiles(path, extensionTextMask))

#should i use os.walk instead?
def getFiles(path, extensionTextMask = ""):
	if extensionTextMask == "":
		return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f))]
	else:
		return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)) 
				and getExtensionText(os.path.join(path,f)) == extensionTextMask]

def getDirCount(path):
	return len(getDirs(path))

def getDirs(path):
	return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]

def parseFloatVector(expectedVec):
	parts = expectedVec.split(',')
	vec = []
	for i,p in enumerate(parts):
		vec.append(float(p))
	return vec

def parseIntVector(expectedVec):
	parts = expectedVec.split(',')
	vec = []
	for i,p in enumerate(parts):
		vec.append(int(p))
	return vec

def argFileValidity(files, target_argfile):
	#now for the argfile cases
	if len(files) == 1 and target_argfile != "" and target_argfile != files[0]:
		print("error, mismatch between specified arg file and arg file found in directory! QUIT")
		exit()
	elif len(files) == 1 and target_argfile == "":
		print("using current argfile in directory: \""+files[0]+"\", good to go!")
		return files[0]
	elif len(files) > 1 and target_argfile not in files:
		print("error, target argfile not found in directory, and too many to decide! QUIT")
		exit()
	elif len(files) > 1 and target_argfile in files:
		print("target argfile is in directory: \""+target_argfile+"\", good to go!")
	else:
		print("target argfile exists: \""+target_argfile+"\", good to go!")
	return target_argfile