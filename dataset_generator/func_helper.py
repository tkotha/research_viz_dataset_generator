import os
import os.path
import sys
import random
import numpy
import math
import noise #we will be using this for our perlin noise most likely
from helper import *
from model_helper import *
#we need to return an array of functions, and somehow 'group' them into one unit for the dataset generator
#------------------FUNC FILE RELATED HELPER FUNCTIONS-------------------

def OpenFuncSet(funcFile):
	newfuncset = []
	with open(funcFile, 'r') as f:
		for line in f:
			parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None]]
			func = []
			for i,p in enumerate(parts):
				func.append(float(p))
			newfuncset.append(func)
	return newfuncset

def OpenSingleFunc(funcFile):
	func = []
	with open(funcFile, 'r') as f:
		for line in f:
			parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None]]
			for i,p in enumerate(parts):
				func.append(float(p))
	return func

#use this to serialize an array of functions to a file
def WriteFuncSet(funcFilePath, funcset):
	with open(funcFilePath, 'w') as f:
		for func in funcset:
			for i,p in enumerate(func):
				if i != len(func)-1:
					f.write(str(p)+" ")
				else:
					f.write(str(p)+"\n")
#use this to serialize one function to a file
def WriteSingleFunc(funcFilePath, func):
	with open(funcFilePath, 'w') as f:
		for i,ff in enumerate(func):
			if i != len(func) -1:
				f.write(str(ff)+" ")
			else:
				f.write(str(ff)+"\n")




#------------------FUNC GEN RELATED HELPER FUNCTIONS-------------------
#note each of these functions (or rather the 'finalized' format we will be using for the experiment's functions) must include the vertex normals as well

def ValidateDictValue(key, dic, default):
	if key in dic.keys():
		return dic[key]
	else:
		return default

#Arguments: amplitude
def ProcessSaltPepperNoise(vertices, highResVertMap, args, PRECISION = 6):
	func = []
	Amplitude = ValidateDictValue("amplitude", args, 1)
	for i in range(0,len(vertices)):
		func.append(round(random.uniform(-Amplitude, Amplitude),PRECISION))
	return [func, func]


#Gauss functions
#Arguments: amplitude, stdvec(3d vec), position(3d vec)
def Process3DGauss(vertices, highResVertMap, args):
	func = []
	Amplitude = ValidateDictValue("amplitude",args, 1)
	stdvec = ValidateDictValue("stdvec", args, [1,1,1])
	while len(stdvec) != 3:
		stdvec.append(1)
	position = ValidateDictValue("position", args, [0,0,0])
	for i in range(0,len(vertices)):
		vertex = vertices[i]
		stdvx = stdvec[0]
		if stdvx == 0:
			stdvx = 1
		stdvy = stdvec[1]
		if stdvy == 0:
			stdvy = 1
		stdvz = stdvec[2]
		if stdvz == 0:
			stdvz = 1
		xpart = numpy.power(vertex[0] - position[0], 2)/ (2*numpy.power(stdvx,2))
		ypart = numpy.power(vertex[1] - position[1], 2)/ (2*numpy.power(stdvy,2))
		zpart = numpy.power(vertex[2] - position[2], 2)/ (2*numpy.power(stdvz,2))
		func.append(Amplitude * numpy.exp(-(xpart + ypart + zpart)))
	return [func, func]

def Process3DGaussOnePoint(vertex, position, amplitude, standard_deviation):
	xpart = numpy.power(vertex[0] - position[0], 2)/ (2*numpy.power(standard_deviation[0], 2))
	ypart = numpy.power(vertex[1] - position[1], 2)/ (2*numpy.power(standard_deviation[1], 2))
	zpart = numpy.power(vertex[2] - position[2], 2)/ (2*numpy.power(standard_deviation[2], 2))
	return amplitude * numpy.exp(-(xpart + ypart + zpart))

def ProcessPerlin3DOnePoint(vertex, amplitude, offset):
	return abs(amplitude* noise.pnoise3(vertex[0], vertex[1], vertex[2], 5, 1, 2, 128, 128, 128, offset))

#Arguments: amplitude, stdvec(2d vec), position(2d vec)
def Process2DGauss(vertices, highResVertMap, args):
	func = []
	Amplitude = ValidateDictValue("amplitude",args, 1)
	stdvec = ValidateDictValue("stdvec", args, [1,1])
	while len(stdvec) != 2:
		stdvec.append(1)
	position = ValidateDictValue("position", args, [0,0])
	for i in range(0,len(vertices)):
		vertex = vertices[i]
		stdvx = stdvec[0]
		if stdvx == 0:
			stdvx = 1
		stdvy = stdvec[1]
		if stdvy == 0:
			stdvy = 1
		xpart = numpy.power(vertex[0] - position[0], 2)/ (2*numpy.power(stdvx,2))
		ypart = numpy.power(vertex[1] - position[1], 2)/ (2*numpy.power(stdvy,2))
		func.append(Amplitude * numpy.exp(-(xpart + ypart)))
	return [func, func]


#here is where we generate the empty func -- pretty stupid, but whatever
#no arguments, but to stay consistent
def ProcessEmpty(vertices, highResVertMap, args):
	func = []
	for i in range(0, len(vertices)):
		func.append(0)
	return [func, func]

def ProcessZ(vertices, highResVertMap, args):
	func = []
	for i in range(0, len(vertices)):
		func.append(vertices[i][2])
	return [func, func]

def ProcessY(vertices, highResVertMap, args):
	func = []
	for i in range(0, len(vertices)):
		func.append(vertices[i][1])
	return [func, func]

def ProcessX(vertices, highResVertMap, args):
	func = []
	for i in range(0, len(vertices)):
		func.append(vertices[i][0])
	return [func, func, func]

#does this really need to return an id? how about just a point?
def GetGeodesicPointFromDist(VertMap, vid, radius, Epsilon):
	vA = VertMap[vid]
	vApos = vA["pos"]
	candidate_list = []
	seenverts = set()
	q = []
	q.append([vid, 0])
	while len(q) != 0:
		curV, curdist = tuple(q.pop(0))
		neighbors = VertMap[curV]["neighbors"]
		curpos = VertMap[curV]["pos"]
		for n in neighbors:
			if n not in seenverts:
				seenverts.add(n)
				npos = VertMap[n]["pos"]
				dist = numpy.sqrt(numpy.power(curpos[0] - npos[0], 2) + numpy.power(curpos[1] - npos[1], 2) +numpy.power(curpos[2] - npos[2], 2))
				if curdist + dist >= radius:
					#get the projected point
					leftoverDist = abs(radius - curdist)
					#now get the projected point
					candidate_point = [(npos[0] - curpos[0])/dist,  (npos[1] - curpos[1])/dist, (npos[2] - curpos[2])/dist]
					candidate_point = [ curpos[0] + candidate_point[0]*leftoverDist, \
									    curpos[1] + candidate_point[1]*leftoverDist, \
									    curpos[2] + candidate_point[2]*leftoverDist]
					candidate_list.append([n, candidate_point, curdist+dist, \
						numpy.sqrt(numpy.power(vApos[0] - npos[0], 2) + numpy.power(vApos[1] - npos[1], 2) +numpy.power(vApos[2] - npos[2], 2))])
				else:
					q.append([n, curdist+dist])


	#since all points given are projected to us, we can just select them as we wish.
	#now if we get an assertion failure, it should only be because the BFS walk ENTIRELY FAILED
	if len(candidate_list) != 0:
		return candidate_list[random.randrange(0, len(candidate_list))][1]
	else: return -1


# // scaleGauss::
# // repeat = 500
# // isRandomPerTrial = True
# // isVertRandom = True
# // APrimeDist = .15   #this is actually a derived attribute
# // A1PrimeDist = .55
# // A0PrimeDist = .05
# // desiredSNR = 5
# // numOfFeatures = 2
# // fixedAmplitude = 1.0
# // fixedStdVec = 1.0, 1.0, 1.0
# // noiseType = perlin
# // epsilon = .1

def ProcessScaleGauss3Points(vertices, highResVertMap, args):
	isRandomPerTrial = ValidateDictValue("isRandomPerTrial", args, False)
	isVertRandom = ValidateDictValue("isVertRandom", args, False)
	APrimeDist = ValidateDictValue("APrimeDist", args, 1.0)
	A1PrimeDist = ValidateDictValue("A1PrimeDist", args, 1.0)
	A0PrimeDist = ValidateDictValue("A0PrimeDist", args, 1.0)
	desiredSNR = ValidateDictValue("desiredSNR", args, 5)
	if "numOfFeatures" in args:
		numOfFeatures = ValidateDictValue("numOfFeatures", args, 2)
	elif "numOfFeaturesRange" in args:
		numOfFeatures = int(random.choice(ValidateDictValue("numOfFeaturesRange", args, [2, 10])))
	else:
		numOfFeatures = 2
	noiseType = ValidateDictValue("noiseType", args, "perlin")
	fixedAmplitude = ValidateDictValue("fixedAmplitude", args, 1.0)
	fixedStdVec = ValidateDictValue("fixedStdVec", args, [1.0,1.0,1.0])
	epsilon = ValidateDictValue("epsilon", args, .1)
	b_points = []
	while len(b_points) < numOfFeatures-1:
		new_bpoint = random.choice(list(highResVertMap.keys()))
		if new_bpoint not in b_points:
			b_points.append(new_bpoint)

	a_point = -1
	while a_point == -1:
		new_apoint = random.choice(list(highResVertMap.keys()))
		if new_apoint not in b_points:
			a_point = new_apoint
	
	#here the a_prime_point is much easier to calculate
	a_prime0_point = a_point
	a_prime1_point = a_point

	perlin_verts_base = []
	perlin_sum_base = 0.0

	perlin_verts0 = []
	perlin_sum0 = 0.0

	perlin_verts1 = []
	perlin_sum1 = 0.0

	gaussA_verts_base = []
	gaussA_sum_base = 0.0

	gaussA_prime0_verts = []
	gaussA_prime0_sum = 0.0

	gaussA_prime1_verts = []
	gaussA_prime1_sum = 0.0

	for vi, vert in enumerate(vertices):
		new_perlin_base = ProcessPerlin3DOnePoint(vert, 1.0, 1776)
		new_perlin0 = ProcessPerlin3DOnePoint(vert, 1.0, 133)
		new_perlin1 = ProcessPerlin3DOnePoint(vert, 1.0, 5620)

		perlin_verts_base.append(new_perlin_base)
		perlin_sum_base += new_perlin_base

		perlin_verts0.append(new_perlin0)
		perlin_sum0 += new_perlin0

		perlin_verts1.append(new_perlin1)
		perlin_sum1 += new_perlin1


		bsum = 0
		for b in b_points:
			bsum += Process3DGaussOnePoint(vert, highResVertMap[b]["pos"], fixedAmplitude, fixedStdVec)

		asum = Process3DGaussOnePoint(vert, highResVertMap[a_point]["pos"], fixedAmplitude, fixedStdVec)
		#we may need to change the formula here to fixedAmplitude - Aprimedist? we want to get the difference between the prior amplitude, but b4, it wouldve just given us the global value
		a_prime0_sum = Process3DGaussOnePoint(vert, highResVertMap[a_prime0_point]["pos"], max(0, fixedAmplitude - A0PrimeDist), fixedStdVec)
		a_prime1_sum = Process3DGaussOnePoint(vert, highResVertMap[a_prime1_point]["pos"], max(0, fixedAmplitude - A1PrimeDist), fixedStdVec)

		gaussA_total = bsum + asum
		gaussA_prime0_total = bsum + a_prime0_sum
		gaussA_prime1_total = bsum + a_prime1_sum

		gaussA_verts_base.append(gaussA_total)
		gaussA_sum_base += gaussA_total

		gaussA_prime0_verts.append(gaussA_prime0_total)
		gaussA_prime0_sum += gaussA_prime0_total

		gaussA_prime1_verts.append(gaussA_prime1_total)
		gaussA_prime1_sum += gaussA_prime1_total

	perlin_identical = True
	for pi, perlb in enumerate(perlin_verts_base):
		perl0 = perlin_verts0 [pi]
		perl1 = perlin_verts1 [pi]
		if perl0 != perl1 or perl1 != perlb or perlb != perl0:
			perlin_identical = False
			break

	assert perlin_identical == False

	SNRA = float(gaussA_sum_base)/float(perlin_sum_base)
	alpha = SNRA/desiredSNR


	func1 = []
	func2 = []
	func3 = []
	for gi, gaussA_base in enumerate(gaussA_verts_base):
		gaussA_prime0 = gaussA_prime0_verts[gi]
		gaussA_prime1 = gaussA_prime1_verts[gi]

		perlin_base = perlin_verts_base[gi]
		perlin0 = perlin_verts0[gi]
		perlin1 = perlin_verts1[gi]

		func1.append(gaussA_base + perlin_base * alpha)
		func2.append(gaussA_prime0 + perlin0 * alpha)
		func3.append(gaussA_prime1 + perlin1 * alpha)


	return [func1, func2, func3]


def ProcessScaleGauss(vertices, highResVertMap, args):
	isRandomPerTrial = ValidateDictValue("isRandomPerTrial", args, False)
	isVertRandom = ValidateDictValue("isVertRandom", args, False)
	APrimeDist = ValidateDictValue("APrimeDist", args, 1.0)
	# APrimeDistInc - I dont think I use this here...
	desiredSNR = ValidateDictValue("desiredSNR", args, 5)
	if "numOfFeatures" in args:
		numOfFeatures = ValidateDictValue("numOfFeatures", args, 2)
	elif "numOfFeaturesRange" in args:
		numOfFeatures = int(random.choice(ValidateDictValue("numOfFeaturesRange", args, [2, 10])))
	else:
		numOfFeatures = 2
	noiseType = ValidateDictValue("noiseType", args, "perlin")
	fixedAmplitude = ValidateDictValue("fixedAmplitude", args, 1.0)
	fixedStdVec = ValidateDictValue("fixedStdVec", args, [1.0,1.0,1.0])
	epsilon = ValidateDictValue("epsilon", args, .1)
	b_points = []

	while len(b_points) < numOfFeatures-1:
		new_bpoint = random.choice(list(highResVertMap.keys()))
		if new_bpoint not in b_points:
			b_points.append(new_bpoint)

	a_point = -1
	while a_point == -1:
		new_apoint = random.choice(list(highResVertMap.keys()))
		if new_apoint not in b_points:
			a_point = new_apoint

	#here the a_prime_point is much easier to calculate
	a_prime_point = a_point

	perlin_verts1 = []
	perlin_sum1 = 0.0

	perlin_verts2 = []
	perlin_sum2 = 0.0

	gaussA_verts = []
	gaussA_sum = 0.0

	gaussA_prime_verts = []
	gaussA_prime_sum = 0.0

	for vi, vert in enumerate(vertices):
		new_perlin1 = ProcessPerlin3DOnePoint(vert, 1.0, 133)
		new_perlin2 = ProcessPerlin3DOnePoint(vert, 1.0, 5620)

		perlin_verts1.append(new_perlin1)
		perlin_sum1 += new_perlin1

		perlin_verts2.append(new_perlin2)
		perlin_sum2 += new_perlin2


		bsum = 0
		for b in b_points:
			bsum += Process3DGaussOnePoint(vert, highResVertMap[b]["pos"], fixedAmplitude, fixedStdVec)

		asum = Process3DGaussOnePoint(vert, highResVertMap[a_point]["pos"], fixedAmplitude, fixedStdVec)
		#we may need to change the formula here to fixedAmplitude - Aprimedist? we want to get the difference between the prior amplitude, but b4, it wouldve just given us the global value
		a_prime_sum = Process3DGaussOnePoint(vert, highResVertMap[a_prime_point]["pos"], max(0, fixedAmplitude - APrimeDist), fixedStdVec)

		gaussA_total = bsum + asum
		gaussA_prime_total = bsum + a_prime_sum

		gaussA_verts.append(gaussA_total)
		gaussA_sum += gaussA_total

		gaussA_prime_verts.append(gaussA_prime_total)
		gaussA_prime_sum += gaussA_prime_total

	perlin_identical = True
	for pi, perl1 in enumerate(perlin_verts1):
		perl2 = perlin_verts2[pi]
		if perl2 != perl1:
			perlin_identical = False

	assert perlin_identical == False

	SNRA = gaussA_sum/perlin_sum1
	alpha = SNRA/desiredSNR


	func1 = []
	func2 = []

	for gi, gaussA in enumerate(gaussA_verts):
		gaussA_prime = gaussA_prime_verts[gi]
		perlin1 = perlin_verts1[gi]
		perlin2 = perlin_verts2[gi]

		func1.append(gaussA + perlin1 * alpha)
		func2.append(gaussA_prime + perlin2 * alpha)


	return [func1, func2]



# // positionGauss::
# // repeat = 500
# // isRandomPerTrial = True
# // isVertRandom = True
# // APrimeDist = .15   
# // A1PrimeDist = .55  #this is actually a derived attribute
# // A0PrimeDist = .05  #this is actually a derived attribute
# // desiredSNR = 5
# // numOfFeatures = 2
# // fixedAmplitude = 1.0
# // fixedStdVec = 1.0, 1.0, 1.0
# // noiseType = perlin
# // epsilon = .1
def ProcessPositionalGauss3Points(vertices, highResVertMap, args):
	sRandomPerTrial = ValidateDictValue("isRandomPerTrial", args, False)
	isVertRandom = ValidateDictValue("isVertRandom", args, False)
	APrimeDist = ValidateDictValue("APrimeDist", args, 1.0)
	A0PrimeDist = ValidateDictValue("A0PrimeDist", args, 1.0)
	A1PrimeDist = ValidateDictValue("A1PrimeDist", args, 1.0)
	# APrimeDistInc - I dont think I use this here...
	desiredSNR = ValidateDictValue("desiredSNR", args, 5)
	if "numOfFeatures" in args:
		numOfFeatures = ValidateDictValue("numOfFeatures", args, 2)
	elif "numOfFeaturesRange" in args:
		numOfFeatures = int(random.choice(ValidateDictValue("numOfFeaturesRange", args, [2, 10])))
	else:
		numOfFeatures = 2
	noiseType = ValidateDictValue("noiseType", args, "perlin")
	fixedAmplitude = ValidateDictValue("fixedAmplitude", args, 1.0)
	fixedStdVec = ValidateDictValue("fixedStdVec", args, [1.0,1.0,1.0])
	epsilon = ValidateDictValue("epsilon", args, .1)
	b_points = []

	while len(b_points) < numOfFeatures-1:
		new_bpoint = random.choice(list(highResVertMap.keys()))
		if new_bpoint not in b_points:
			b_points.append(new_bpoint)

	a_point = -1
	while a_point == -1:
		new_apoint = random.choice(list(highResVertMap.keys()))
		if new_apoint not in b_points:
			a_point = new_apoint

	#here the a_prime_point is much easier to calculate
	a_prime0_point = GetGeodesicPointFromDist(highResVertMap, a_point, A0PrimeDist, epsilon)
	assert a_prime0_point != -1
	a_prime1_point = GetGeodesicPointFromDist(highResVertMap, a_point, A1PrimeDist, epsilon)
	assert a_prime1_point != -1

	perlin_verts_base = []
	perlin_sum_base = 0.0

	perlin_verts0 = []
	perlin_sum0 = 0.0

	perlin_verts1 = []
	perlin_sum1 = 0.0

	gaussA_verts_base = []
	gaussA_sum_base = 0.0

	gaussA_prime0_verts = []
	gaussA_prime0_sum = 0.0

	gaussA_prime1_verts = []
	gaussA_prime1_sum = 0.0

	for vi, vert in enumerate(vertices):
		new_perlin_base = ProcessPerlin3DOnePoint(vert, 1.0, 1776)
		new_perlin0 = ProcessPerlin3DOnePoint(vert, 1.0, 133)
		new_perlin1 = ProcessPerlin3DOnePoint(vert, 1.0, 5620)

		perlin_verts_base.append(new_perlin_base)
		perlin_sum_base += new_perlin_base

		perlin_verts0.append(new_perlin0)
		perlin_sum0 += new_perlin0

		perlin_verts1.append(new_perlin1)
		perlin_sum1 += new_perlin1


		bsum = 0
		for b in b_points:
			bsum += Process3DGaussOnePoint(vert, highResVertMap[b]["pos"], fixedAmplitude, fixedStdVec)

		asum = Process3DGaussOnePoint(vert, highResVertMap[a_point]["pos"], fixedAmplitude, fixedStdVec)
		a_prime0_sum = Process3DGaussOnePoint(vert, a_prime0_point, fixedAmplitude, fixedStdVec)
		a_prime1_sum = Process3DGaussOnePoint(vert, a_prime1_point, fixedAmplitude, fixedStdVec)

		gaussA_total = bsum + asum
		gaussA_prime0_total = bsum + a_prime0_sum
		gaussA_prime1_total = bsum + a_prime1_sum

		gaussA_verts_base.append(gaussA_total)
		gaussA_sum_base += gaussA_total

		gaussA_prime0_verts.append(gaussA_prime0_total)
		gaussA_prime0_sum += gaussA_prime0_total

		gaussA_prime1_verts.append(gaussA_prime1_total)
		gaussA_prime1_sum += gaussA_prime1_total

	perlin_identical = True
	for pi, perlb in enumerate(perlin_verts_base):
		perl0 = perlin_verts0 [pi]
		perl1 = perlin_verts1 [pi]
		if perl0 != perl1 or perl1 != perlb or perlb != perl0:
			perlin_identical = False
			break

	assert perlin_identical == False

	SNRA = float(gaussA_sum_base)/float(perlin_sum_base)
	alpha = SNRA/desiredSNR


	func1 = []
	func2 = []
	func3 = []
	for gi, gaussA_base in enumerate(gaussA_verts_base):
		gaussA_prime0 = gaussA_prime0_verts[gi]
		gaussA_prime1 = gaussA_prime1_verts[gi]

		perlin_base = perlin_verts_base[gi]
		perlin0 = perlin_verts0[gi]
		perlin1 = perlin_verts1[gi]

		func1.append(gaussA_base + perlin_base * alpha)
		func2.append(gaussA_prime0 + perlin0 * alpha)
		func3.append(gaussA_prime1 + perlin1 * alpha)


	return [func1, func2, func3]

def ProcessPositionalGauss(vertices, highResVertMap, args):
	isRandomPerTrial = ValidateDictValue("isRandomPerTrial", args, False)
	isVertRandom = ValidateDictValue("isVertRandom", args, False)
	APrimeDist = ValidateDictValue("APrimeDist", args, 1.0)
	# APrimeDistInc - I dont think I use this here...
	desiredSNR = ValidateDictValue("desiredSNR", args, 5)
	if "numOfFeatures" in args:
		numOfFeatures = ValidateDictValue("numOfFeatures", args, 2)
	elif "numOfFeaturesRange" in args:
		numOfFeatures = int(random.choice(ValidateDictValue("numOfFeaturesRange", args, [2, 10])))
	else:
		numOfFeatures = 2
	noiseType = ValidateDictValue("noiseType", args, "perlin")
	fixedAmplitude = ValidateDictValue("fixedAmplitude", args, 1.0)
	fixedStdVec = ValidateDictValue("fixedStdVec", args, [1.0,1.0,1.0])
	epsilon = ValidateDictValue("epsilon", args, .1)
	b_points = []

	while len(b_points) < numOfFeatures-1:
		new_bpoint = random.choice(list(highResVertMap.keys()))
		if new_bpoint not in b_points:
			b_points.append(new_bpoint)

	a_point = -1
	while a_point == -1:
		new_apoint = random.choice(list(highResVertMap.keys()))
		if new_apoint not in b_points:
			a_point = new_apoint

	a_prime_point = GetGeodesicPointFromDist(highResVertMap, a_point, APrimeDist, epsilon)
	assert a_prime_point != -1

	perlin_verts1 = []
	perlin_sum1 = 0.0

	perlin_verts2 = []
	perlin_sum2 = 0.0

	gaussA_verts = []
	gaussA_sum = 0.0

	gaussA_prime_verts = []
	gaussA_prime_sum = 0.0

	for vi, vert in enumerate(vertices):
		new_perlin1 = ProcessPerlin3DOnePoint(vert, 1.0, 133)
		new_perlin2 = ProcessPerlin3DOnePoint(vert, 1.0, 5620)

		perlin_verts1.append(new_perlin1)
		perlin_sum1 += new_perlin1

		perlin_verts2.append(new_perlin2)
		perlin_sum2 += new_perlin2


		bsum = 0
		for b in b_points:
			bsum += Process3DGaussOnePoint(vert, highResVertMap[b]["pos"], fixedAmplitude, fixedStdVec)

		asum = Process3DGaussOnePoint(vert, highResVertMap[a_point]["pos"], fixedAmplitude, fixedStdVec)
		a_prime_sum = Process3DGaussOnePoint(vert, a_prime_point, fixedAmplitude, fixedStdVec)

		gaussA_total = bsum + asum
		gaussA_prime_total = bsum + a_prime_sum

		gaussA_verts.append(gaussA_total)
		gaussA_sum += gaussA_total

		gaussA_prime_verts.append(gaussA_prime_total)
		gaussA_prime_sum += gaussA_prime_total

	perlin_identical = True
	for pi, perl1 in enumerate(perlin_verts1):
		perl2 = perlin_verts2[pi]
		if perl2 != perl1:
			perlin_identical = False

	assert perlin_identical == False

	SNRA = gaussA_sum/perlin_sum1
	alpha = SNRA/desiredSNR


	func1 = []
	func2 = []

	for gi, gaussA in enumerate(gaussA_verts):
		gaussA_prime = gaussA_prime_verts[gi]
		perlin1 = perlin_verts1[gi]
		perlin2 = perlin_verts2[gi]

		func1.append(gaussA + perlin1 * alpha)
		func2.append(gaussA_prime + perlin2 * alpha)


	return [func1, func2]



#note: we use the convention of args as a dictionary to make it very easy to modify this as needed
#this will allow us to group multiple instances of function calls simply using strings
#todo: add a combo operator that'll enable us to chain together multiple functions into one file
func_table = {
	"noise" : ProcessSaltPepperNoise,
	"gauss3d" : Process3DGauss,
	"gauss2d" : Process2DGauss,
	"empty" : ProcessEmpty,
	"z" : ProcessZ,
	"y" : ProcessY,
	"x" : ProcessX,
	"positionGauss": ProcessPositionalGauss3Points,
	"scaleGauss": ProcessScaleGauss3Points
}