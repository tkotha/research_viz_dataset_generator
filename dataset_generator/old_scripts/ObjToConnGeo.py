import os
import os.path
import sys
import random
import math
from decimal import Decimal
vertices = []
tris = []

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

def WriteFiles(connFilePath, geoFilePath):
	with open(geoFilePath,"w") as f:
		#first write the vertices
		for i,p in enumerate(vertices):
			f.write("   "+str('%e' % p[0])+"   "+str('%e' % p[1])+"   "+str('%e' % p[2])+"\n")
	with open(connFilePath,"w") as f:
		#then write the tris
		for i,p in enumerate(tris):
			f.write("   "+str('%e' % p[0])+"   "+str('%e' % p[1])+"   "+str('%e' % p[2])+"\n")

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


	connpath = os.path.splitext(args["connFile"])[0]+".txt"
	geopath = os.path.splitext(args["geoFile"])[0]+".txt"
	if not args["connFile"]:
		objfilepath = os.path.splitext(args["objFile"])[0]+"_toConn.txt"
	if not args["geoFile"]:
		objfilepath = os.path.splitext(args["objFile"])[0]+"_toGeo.txt"

	if os.path.isfile(args["objFile"]):
		OpenObj(args["objFile"])
		WriteFiles(connpath, geopath)
		
	else:
		print("Error! path specified is not a file! "+sys.argv[1])