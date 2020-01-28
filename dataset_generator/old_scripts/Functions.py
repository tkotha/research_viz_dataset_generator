import os
import os.path
import sys
import random
import numpy
import math

input_funcset = []
output_funcset = []

#importer for existing function files
def OpenFuncSet(funcFile):
	newfuncset = []
	with open(funcFile) as f:
		for line in f:
			parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None]]
			func = []
			for i,p in enumerate(parts):
				func.append(float(p))
			newfuncset.append(func)
	return newfuncset

#exporter for calculated functionset
def WriteFuncSet(funcFilePath, funcset):
	with open(funcFilePath) as f:
		for func in funcset:
			for i,p in enumerate(func):
				if i != len(func)-1:
					f.write(float(p)+" ")
				else:
					f.write(float(p)+"\n")



#noise model functions
def ProcessSaltPepperNoise(Amplitude):
	func = []
	for i in range(0,len(vertices)):
		func.append(round(random.uniform(-Amplitude, Amplitude),PRECISION))
	return func


#Gauss functions
def Process3DGauss(Amplitude, stdvec, position):
	func = []
	for i in range(0,len(vertices)):
		vertex = vertices[i]
		xpart = numpy.power(vertex[0] - position[0], 2)/ (2*numpy.power(stdvec[0],2))
		ypart = numpy.power(vertex[1] - position[1], 2)/ (2*numpy.power(stdvec[1],2))
		zpart = numpy.power(vertex[2] - position[2], 2)/ (2*numpy.power(stdvec[2],2))
		func.append(Amplitude * numpy.exp(-(xpart + ypart + zpart)))
	return func

def Process2DGauss(Amplitude, stdvec, position):
	func = []
	for i in range(0,len(vertices)):
		vertex = vertices[i]
		xpart = numpy.power(vertex[0] - position[0], 2)/ (2*numpy.power(stdvec[0],2))
		ypart = numpy.power(vertex[1] - position[1], 2)/ (2*numpy.power(stdvec[1],2))
		func.append(Amplitude * numpy.exp(-(xpart + ypart)))
	return func