import os
import os.path
import sys
import random
import math
vertices = []
tris = []

def OpenGeometry(geoFile):
	newverts = []
	with open(geoFile) as f:
		for line in f:
			parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None]]
			pv = []
			for i,p in enumerate(parts):
				pv.append(float(p))
			newverts.append(pv)
	#print(newverts)
	return newverts

def OpenConnections(connFile):
	newtris = []
	minIndex = 5000
	with open(connFile) as f:
		for line in f:
			parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None]]
			pv = []
			for i,p in enumerate(parts):
				pvt = int(float(p)) +1
				if pvt < minIndex:
					minIndex = pvt
				pv.append(pvt)
			newtris.append(pv)
	# print(minIndex)
	return newtris

def WriteObj(objFilePath):
	with open(objFilePath,"w") as f:
		#first write the vertices
		for i,p in enumerate(vertices):
			f.write("v "+str(p[0])+" "+str(p[1])+" "+str(p[2])+"\n")
		#then write the tris
		for i,p in enumerate(tris):
			f.write("f "+str(p[0])+" "+str(p[1])+" "+str(p[2])+"\n")


PRECISION = 9
args = {
	"geoFile": "",
	"connFile":"",
	"objFile":""
	#"numberOfFuncs":"1"
}

if __name__ == "__main__":
	for i in range(1,len(sys.argv)):
		s = sys.argv[i]
		parts = s.split(':')
		if len(parts) != 2:
			print("error, invalid arg "+s)
			exit()
		if parts[0] not in args:
			print("error, unrecognized argument " + parts[0])
		args[parts[0]] = parts[1]


	objfilepath = os.path.splitext(args["objFile"])[0]+".obj"
	if not args["objFile"]:
		objfilepath = os.path.splitext(args["geoFile"])[0]+"_"+os.path.splitext(args["connFile"])[0]+"_toObj.obj"

	if os.path.isfile(args["geoFile"]):
		vertices = OpenGeometry(args["geoFile"])
		if os.path.isfile(args["connFile"]):
			tris = OpenConnections(args["connFile"])
			
			WriteObj(objfilepath)
		else:
			print("Error! path specified is not a file! "+sys.argv[2])
	else:
		print("Error! path specified is not a file! "+sys.argv[1])