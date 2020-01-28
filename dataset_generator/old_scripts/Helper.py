import os
import os.path
import sys
import random
import numpy
import math


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

def parseCSVStringParameters(params):
	parts = params.split(',')
	p = []
	for i,s in enumerate(parts):
		p.append(s.strip())
	return p

def parseFileArgumentLineItem(lineitem):
	parts = lineitem.split(':')
	if len(parts) != 2:
		print("ERROR: Line item must contain 2 elements separated by ':'!   " + lineitem)
		exit()
	parts[0] = parts[0].strip()
	parts[1] = parts[1].strip()
	return parts