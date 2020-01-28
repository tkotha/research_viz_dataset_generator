import os
import os.path
import ntpath
import sys
import random
import numpy
import math
import json

#this is from https://www.pythoncentral.io/pythons-range-function-explained/
def frange(start, stop, step):
	i = start
	while i < stop:
		yield i
		i += step

def map_float(value, in_min, in_max, out_min, out_max):
	denom = float(in_max) - float(in_min)
	if math.isclose(denom, 0, abs_tol = 0.0000000001):
		denom = .0000001
	return out_min + (out_max - out_min) * ((value - in_min)/ denom)



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

def parseBoolAffirmative(value):
	return value in ["True", "true", "yes", "Y", "T", "y","t", "1"]

def parseCSVStringParameters(params):
	parts = params.split(',')
	p = []
	for i,s in enumerate(parts):
		p.append(s.strip())
	return p

def parseFileArgumentLineItem(lineitem, delimiter = ':'):
	parts = lineitem.split(delimiter)
	if len(parts) != 2:
		print("ERROR: Line item must contain 2 elements separated by ':'!   " + lineitem)
		exit()
	parts[0] = parts[0].strip()
	parts[1] = parts[1].strip()
	return parts

def argFileValidity(files, target_argfile):
	#now for the argfile cases
	print(files)
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

#https://stackoverflow.com/questions/541390/extracting-extension-from-filename-in-python
def getExtensionText(filename):
	return os.path.splitext(filename)[1][1:]

def getFileNameText(path):
	head, tail = ntpath.split(path)
	return tail or ntpath.basename(head)
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

#probably slow, but not important atm
def getCommonSubstring(s1, s2):
	substring = ""
	l1 = len(s1)
	l2 = len(s2)
	i = 0
	while i < l1 and i < l2 and s1[i] == s2[i]:
		substring += s1[i]
		i += 1
	return substring

#returns both the bool status and the resulting path as a tuple
def determineAbsOrRelativePath(filepath, possibleBasePath):
	temppath = filepath
	if not os.path.isabs(filepath) and not (filepath.startswith("C:") or filepath.startswith("c:")):
		temppath = os.path.join(possibleBasePath,filepath)
	# print (filepath)
	# print(keyvalue[1])
	#we are assuming here that we are only verifying folders
	return temppath