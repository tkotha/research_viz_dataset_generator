import os
import os.path
import sys
import random
import numpy
import math

vertices = []
tris = []
funcs = []

#importer for rosen's geometry text file
def OpenGeometry(geoFile):
	with open(geoFile) as f:
		for line in f:
			parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None]]
			pv = []
			for i,p in enumerate(parts):
				pv.append(float(p))
			vertices.append(pv)
	

#importer for rosen's connectivity text file
def OpenConnections(connFile):
	with open(connFile) as f:
		for line in f:
			parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None]]
			pv = []
			for i,p in enumerate(parts):
				pv.append(int(float(p)))
			tris.append(pv)


#importer for obj files
def OpenObj(objFilePath):
	with open(objFilePath) as f:
		for line in f:
			if line.startswith("v"):
				parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None,"v"]]
				pv = []
				for i,p in enumerate(parts):
					pv.append(float(p))
				vertices.append(pv)
			elif line.startswith("f"):
				parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None,"f"]]
				pv = []
				for i,p in enumerate(parts):
					pvt = int(float(p)) -1
					pv.append(pvt)
				tris.append(pv)

#export current representation to obj file
def WriteObj(objFilePath):
	with open(objFilePath,"w") as f:
		#first write the vertices
		for i,p in enumerate(vertices):
			f.write("v "+str(p[0])+" "+str(p[1])+" "+str(p[2])+"\n")
		#then write the tris
		for i,p in enumerate(tris):
			f.write("f "+str(p[0])+" "+str(p[1])+" "+str(p[2])+"\n")


#export current representation to rosen's connectivity and geometry scheme
def WriteFiles(connFilePath, geoFilePath):
	with open(geoFilePath,"w") as f:
		#first write the vertices
		for i,p in enumerate(vertices):
			f.write("   "+str('%e' % p[0])+"   "+str('%e' % p[1])+"   "+str('%e' % p[2])+"\n")
	with open(connFilePath,"w") as f:
		#then write the tris
		for i,p in enumerate(tris):
			f.write("   "+str('%e' % p[0])+"   "+str('%e' % p[1])+"   "+str('%e' % p[2])+"\n")
