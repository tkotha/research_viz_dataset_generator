import os
import subprocess
import sys
import math
import numpy
import random
import os.path
import io
import ntpath
import json
import csv
from helper import *
from collections import deque
from recordtype import recordtype
from iso_helper import *
from func_helper import *
from reeb_helper import *
import queue
import pprint
import pbjson
import msgpack
import gzip
import shutil
from zipfile import ZipFile
TVData = recordtype('TVData', 'iso trilist neighbors_trilist maxvert component_id')
VertexChain = recordtype('VertexChain', 'vertices isos isPositive')
ContourData = recordtype('ContourData', 'contour_id contour_centroid triset contour_iso taken')
ReebEndData = recordtype('ReebEndData', 'id iso triset')
ReebWalkerData = recordtype('ReebWalkerData', 'current_vert current_iso contour_id_list history done valid')
ReebWalkers = recordtype('ReebWalkers', 'walkers done winner')
Component = recordtype('Component', 'id vertset triset')

TriBand = recordtype('TriBand', 'vertID targetIso maxIso minIso vertType triangleBandSet edgeList')
TriData = recordtype('TriData', 'va vb vc minIso maxIso triNeighbors')
VertData = recordtype('VertData', 'vid vpos vertNeighbors triNeighbors iso vertNeighborChain vertNeighborTriMap neighborEdgelist')
ArcData = recordtype('ArcData', 'edgeCount startVert startIso endVert endIso contourData')

path_7zip = r"..\external\7-ZipPortable\App\7-Zip\7z.exe"
#------------JSON HELPER FUNCTIONS-------------


def minify(JSON_file_name):
	print(JSON_file_name)
	file_data = open(JSON_file_name, "r", 1).read() # store file info in variable
	json_data = json.loads(file_data) # store in json structure
	json_string = json.dumps(json_data, separators=(',', ":")) # Compact JSON structure
	
	file_name = str(JSON_file_name).replace(".json", "") # remove .json from end of file_name string
	new_file_name = "{0}.json".format(file_name)
	open(new_file_name, "w+", 1).write(json_string) # open and write json_string to file
	
	#now we attempt actual compression. these files will be marked as zip files, so the client MUST unzip them in order to read them correctly
	zip_file_name = "{0}.json.zip".format(file_name)
	print(zip_file_name)
	
	olddir = os.getcwd()
	path7zip = os.path.abspath(path_7zip)
	
	os.chdir('\\'.join(file_name.split('\\')[0:-1]))
	print(path7zip)
	ret = None
	if os.name == 'nt': #this is windows
		ret = subprocess.check_output([path7zip, "a", "-tzip", zip_file_name, new_file_name])#JSON_file_name])
	else:	#for now this is everything else
		ret = subprocess.check_output(["zip", zip_file_name, new_file_name])
	os.chdir(olddir)
	return zip_file_name



#-----------ALL OBJF RELATED HELPER FUNCTIONS----------------------------------------------
#this is to be able to combine a given function file with a mesh in obj format
#we do this to get around the current limitation in recon which doesnt allow for an external function file
#note: implicitly saves to OBJPath
#we return the filename

#question: though we dont need it now, should we add an objf to json converter?

def convertFuncAndOBJToOBJF(OBJPath, FuncPath):
	splice_filefunc = ntpath.basename(FuncPath)
	splice_filefunc = os.path.splitext(splice_filefunc)[0]
	OBJFPath = os.path.splitext(OBJPath)[0] + "_"+splice_filefunc + ".objf"
	with open(OBJPath,'r') as obj, open(FuncPath, 'r') as func, open(OBJFPath, 'w') as objf:
		# print("---VERTICES---\n")
		for funcline in func:
			for f in funcline.split():
				objline = obj.readline()
				for objl in objline.split():
					objf.write(objl+" ")
				objf.write(f+"\n")
		# print("---TRIANGLES---\n")
		for objline in obj:
			objls = objline.split()
			# print(objls)
			assert len(objls) == 4
			objf.write(objls[0]+" "+objls[1]+" "+objls[2]+" "+objls[3]+"\n")
	return OBJFPath

#note: implicitly saves to objfpath
def extractFuncFromOBJF(OBJFPath):
	FuncPath = os.path.splitext(OBJFPath)[0]+'_func.txt'
	with open(OBJFPath,'r') as obj, open(FuncPath,'w') as func:
		funcstr = ""
		for line in obj:
			if line.startswith("v"):
				fnval = line.split()[-1]
				funcstr += (fnval+" ")
			else:
				#make sure to remove the very last space with a newline
				funcstr = funcstr[:-1]
				funcstr += "\n"
				func.write(funcstr)
				break

def convertFuncAndOBJToJSON( OBJPath, FuncPath):
	splice_filefunc = ntpath.basename(FuncPath)
	splice_filefunc = os.path.splitext(splice_filefunc)[0]
	OBJFPath = os.path.splitext(OBJPath)[0] + "_"+splice_filefunc + ".json"
	with open(FuncPath,'r') as func, open(OBJPath, 'r') as obj, open(OBJFPath, 'w') as objf_json:
		vertexlist = []
		funclist = []
		trilist = []
		for funcline in func:
			for f in funcline.split():
				objline = obj.readline()
				objls = objline.split()
				funclist.append(float(f))
				vertexlist.append(float(objls[1]))
				vertexlist.append(float(objls[2]))
				vertexlist.append(float(objls[3]))
		for objline in obj:
			objls = objline.split()
			trilist.append([int(objls[1]) -1, int(objls[2]) -1, int(objls[3]) -1])
		finaljson = {
			"meshes": [{"vertices": vertexlist, "faces": trilist, "iso_data" : funclist}]
		}
		json.dump(finaljson, objf_json, indent=4)

#------------JSON with isoline data-------------------------------------
def convertFuncAndOBJToJSON_WithIsoLines( OBJPath, FuncPath, IsoCount = 100):
	splice_filefunc = ntpath.basename(FuncPath)
	splice_filefunc = os.path.splitext(splice_filefunc)[0]
	objmodel = OpenObj(OBJPath)
	funcmodel = OpenSingleFunc(FuncPath)
	OBJFPath = os.path.splitext(OBJPath)[0] + "_"+splice_filefunc + ".json"

	maxiso = float("-inf")
	miniso = float("inf")

	with open(FuncPath,'r') as func, open(OBJPath, 'r') as obj, open(OBJFPath, 'w') as objf_json:
		vertexlist = []
		funclist = []
		trilist = []
		# iso_vertlist = []
		# iso_linelist = []

		for funcline in func:
			for f in funcline.split():
				objline = obj.readline()
				objls = objline.split()
				ff = float(f)
				funclist.append(ff)
				if ff > maxiso:
					maxiso = ff
				if ff < miniso:
					miniso = ff
				vertexlist.append(float(objls[1]))
				vertexlist.append(float(objls[2]))
				vertexlist.append(float(objls[3]))
		for objline in obj:
			objls = objline.split()
			trilist.append([int(objls[1]) -1, int(objls[2]) -1, int(objls[3]) -1])

		#idiot check on the triangles
		for i,t in enumerate(trilist):
			# print(str(t))
			# print(str(objmodel[1][i]))
			assert t[0] == objmodel[1][i][0] and t[1] == objmodel[1][i][1] and t[2] == objmodel[1][i][2]

		#idiot check on functions
		for i,f in enumerate(funclist):
			assert f == funcmodel[i]

		#idiot check on vertices
		for i,v in enumerate(vertexlist):
			#wow this actually works!?
			assert v == objmodel[0][int(i/3)][int(i % 3)]

		#now produce the range of acceptable values for the iso line count
		isodistance =  maxiso - miniso
		isointerval = isodistance / float(IsoCount)
		user_isos = []
		for fi in frange(miniso, maxiso, isointerval):
			user_isos.append(fi)

		#now compute the needed data for isolines
		#store the data in an isodata tuple. note: [0] holds the vertices, [1] holds the line indices
		isodata, vertcount = CreateIsoLineData(user_isos, maxiso, miniso, objmodel[0], 3, trilist, funcmodel)
		finaljson = {
			"meshes": [{"vertices": vertexlist, 
						"faces": trilist, 
						"iso_data" : funclist,
						"iso_verts": isodata[0],
						"iso_lines": isodata[1],
						"max_iso" : maxiso,
						"min_iso" : miniso
						}]
		}
		json.dump(finaljson, objf_json, indent=4)


#------------JSON with isoline data and reeb graph-------------------------------------
#Because we most likely plan on using catmull rom curves in the visualizer portion, we dont need as many iso contours to get us going
def convertFuncAndOBJToJSON_WithIsoAndReeb(OBJPath, FuncPath, ReebPath, CSVPath, ContourGroupingEpsilon = .01, GroupingStrategy = 1, IsoCount = 25):
	splice_filefunc = ntpath.basename(FuncPath)
	splice_filefunc = os.path.splitext(splice_filefunc)[0]
	splice_filereeb = ntpath.basename(ReebPath)
	splice_filereeb = os.path.splitext(splice_filereeb)[0]
	objmodel = OpenObj(OBJPath)
	funcmodel = OpenSingleFunc(FuncPath)
	reebmodel = OpenReebGraph(ReebPath)
	csvmodel = ""
	print("Contour Grouping Epsilon value: "+ str(ContourGroupingEpsilon))
	with open(CSVPath,'r') as csvfile:
		for line in csvfile:
			csvmodel += line 
	OBJFileName = os.path.splitext(OBJPath)[0]
	OBJFPath =  OBJFileName + "_"+splice_filefunc +"_" + splice_filereeb+ ".json"
	IsoJSONPath = OBJFileName+"_"+splice_filefunc+"_iso.json"
	ReebJSONPath = OBJFileName+"_"+splice_filefunc+"_reeb.json"
	FuncJSONPath = OBJFileName+"_"+splice_filefunc+"_func.json"
	# ModelJSONPath = OBJFileName+"_model.json"

	maxiso = float("-inf")
	miniso = float("inf")

	finaljson = None
	iso_json = None
	reeb_json = None
	func_json = None

	with open(FuncPath,'r') as func, open(OBJPath, 'r') as obj, open(OBJFPath, 'w') as objf_json, open(IsoJSONPath, 'w') as isojson, open(ReebJSONPath, 'w') as reebjson, open(FuncJSONPath, 'w') as funcjson:
		vertexlist = []
		funclist = []
		trilist = []
		# iso_vertlist = []
		# iso_linelist = []

		for funcline in func:
			for f in funcline.split():
				objline = obj.readline()
				objls = objline.split()
				ff = float(f)
				funclist.append(ff)
				if ff > maxiso:
					maxiso = ff
				if ff < miniso:
					miniso = ff
				vertexlist.append(float(objls[1]))
				vertexlist.append(float(objls[2]))
				vertexlist.append(float(objls[3]))
		for objline in obj:
			objls = objline.split()
			trilist.append([int(objls[1]) -1, int(objls[2]) -1, int(objls[3]) -1])

		#idiot check on the triangles
		for i,t in enumerate(trilist):
			# print(str(t))
			# print(str(objmodel[1][i]))
			assert t[0] == objmodel[1][i][0] and t[1] == objmodel[1][i][1] and t[2] == objmodel[1][i][2]

		#idiot check on functions
		for i,f in enumerate(funclist):
			assert f == funcmodel[i]

		#idiot check on vertices
		for i,v in enumerate(vertexlist):
			#wow this actually works!?
			assert v == objmodel[0][int(i/3)][int(i % 3)]

		#now produce the range of acceptable values for the iso line count
		# isodistance =  maxiso - miniso
		# isointerval = isodistance / float(IsoCount)
		# user_isos = []
		# for fi in frange(miniso, maxiso, isointerval):
		# 	user_isos.append(fi)


		# grouping strategy:
		#	1 - we group by vertices first - susceptible to local maxima changes, derailing expected trajectory
		#   2 - we group by edges first - gets too many arcs, and we dont have an effective way of filtering them
		#
		#	both styles will adapt the reeb walker
		#

		aggregate_contour_data = []
		debug_centroid_list = []
		totalVertCount = 0
		
		#vertcount formula: len(vertexlist) / 3

		
		edges = reebmodel[1]
		verts = reebmodel[0]
		arcset = dict()
		#create the arcset
		ecount = len(edges)
		for ei, edge in enumerate(edges):
			e1, e2 = tuple(edge)
			if e1 not in arcset:
				arcset[e1] = dict()
			if e2 not in arcset[e1]:
				startiso = None
				endiso = None
				for vert in verts:
					vid, iso = tuple(vert)
					if vid == e1:
						startiso = iso
					elif vid == e2:
						endiso = iso
				assert startiso is not None and endiso is not None
				# isoDist = endiso - startiso
				# tempIsoCount = 8
				# isoInterval = isoDist / float(tempIsoCount)
				# isoEpsilon = abs(isoDist * ContourGroupingEpsilon)
				# user_isos = []
				# for fi in frange(startiso + isoEpsilon, endiso - isoEpsilon, isoInterval):
				# 	user_isos.append(fi)
				# print("Creating new Arcset for " + str(e1) +", "+ str(e2)+":: " + str(ecount - (ei+1)) +" edges remaining...")
				# newContourData, vertcount = CreateIsoLineData(user_isos, objmodel[0], 3, trilist, funcmodel)
				# totalVertCount += vertcount
				arcset[e1][e2] = ArcData(edgeCount = 1, startVert = e1, endVert = e2, startIso = startiso, endIso = endiso, contourData= None)#newContourData)
			else:
				arcset[e1][e2].edgeCount += 1

		#this will be our model for traversal calculations
		tvmap = CreateTVMap(int(len(vertexlist)/3), funclist, trilist, objmodel[0])
		vertmap = CreateVertMap(int(len(vertexlist)/3), trilist, objmodel[0])
		pp = pprint.PrettyPrinter(indent = 3)
		# pp.pprint(arcset)

		#when distinguishing between up or down saddles, you can just use the edgecount in the arcset data to distinguish that
		triangle_bands = []
		for v in verts:
			band = CreateTriangleBands(v[0],v[1],tvmap)
			triangle_bands.append(band)
			for e in edges:
				if e[0] == v[0]:
					band.edgeList.append(e)


		#due to the unruly amount of edge cases, we cannot garauntee that maxpaths are greater than the edge list. so we'll just have to do a best fit
		# for band in triangle_bands:
		# 	if band.vertType == "max": continue
		# 	vertex = tvmap["verts"][band.vertID]
		# 	maxpaths = vertex.vertNeighborChain["maxpaths"]
		# 	assert len(maxpaths) >= len(band.edgeList)

		# pp.pprint(triangle_bands)
		processedEdges = []
		for band in triangle_bands:
			if band.vertType == "max": continue
			vertex = tvmap["verts"][band.vertID]
			maxpaths = vertex.vertNeighborChain["maxpaths"]

			#do contour processing somewhere here? (this probably has to be stored along with the edgelist...)
			#the arcset should now have all the necessary information
			#what we should do now is create an "edge checklist", which tells us what edges need data to be populated
			#then we query the arcset to pull out the contour data as needed
			
			edgeChecklist = []
			curmaxpath = 0
			for e in band.edgeList:
				#schema: start index, end index, was processed?, centroidList, contouridlist, has_candidate?, starting_maxpath
				edgeChecklist.append([e[0],e[1], False, [], [], False, maxpaths[curmaxpath]])
				curmaxpath = (curmaxpath + 1) % len(maxpaths)
			
			#we will be doing contour grouping in two passes
			#this first pass is just to collect ALL POSSIBLE PATHS from a given start vertex
			#we need to ensure that a) there's at least as many walks as required, and b)all edges are accounted for, otherwise there's something inherently wrong with the data
			#we should expect a structure of [ [start_reebvert_id, end_reebvert_id, walkhistory = [vertid, ...]], ...]
			# reebwalk_candidates = ReebWalker(triangle_bands, tvmap, vertex, band, processedEdges)
			reebwalk_candidates = []
			#change of plans: instead of generating candidates, we will just use basic BFS on the check list itself. It knows already what edges it wants, and as long as using maxpaths form the arcs, we should be fine
			#this would be the transparent justification of ensuring we are following recon's source code anyways

			# print("Candidate List: ")
			# for candidate in reebwalk_candidates:
			# 	for e in edgeChecklist:
			# 		if candidate[0] == e[0] and candidate[1] == e[1]:
			# 			e[5] =True
			# 			break
			# 	print([candidate[0], candidate[1]])

			#todo: convert this edge checklist code to account for multiple instances of 1 edge, and modify the BFS walk to aggregate multiple unique routes
			#		we will have to go back to using TVMaps to take into account the disjoint sets for positive traversal. once those sets are found, we just use those as the starting point and then do bfs traversal from there
			hasCandidateMatches = True
			print("Check List: ")
			for e in edgeChecklist:
				print([e[0],e[1]])
				new_candidate = StupidReebWalkBFS(e[6], e[1], vertmap)
				#concatinate the starting_maxpath to our walk
				new_candidate[2] = [e[6]] + new_candidate[2]
				#and make sure to replace our reeb start with the proper reeb start vertex
				new_candidate[0] = e[0]
				if len(new_candidate) != 0:
					print("Walk : "+str(new_candidate[2]))
					reebwalk_candidates.append(new_candidate)
					e[5] = True
				hasCandidateMatches = hasCandidateMatches and e[5]
				if hasCandidateMatches:
					print("---matched!")
				else:
					print("!!!!!FAILED!!!!!")
			assert hasCandidateMatches
			print("has matches!")
			# pp.pprint(reebwalk_candidates)
			#once we have our candidates, for each candidate, match it against an edge in the checklist
			#proceed with contour grouping, keeping track of the id list as well. 
			#if the edge was not previously written to, write to it now
			#if the edge was previously written to, also check to see if a lot of our paths match, if so, we need to reject duplicates
			for candidate in reebwalk_candidates:
				start_reebvert_id = candidate[0]
				end_reebvert_id = candidate[1]
				print("NEW CANDIDATE-----")
				print(candidate)
				print([start_reebvert_id, end_reebvert_id])
				print("---")
				# for e1 in arcset.keys():
				# 	for e2 in arcset[e1].keys():
				# 		print([e1,e2])

				#handle all invalid edges here... I'm not sure we want to do this, b/c it implies we're ignoring a crucial flaw in the traversal... we'll see
				if start_reebvert_id not in arcset or end_reebvert_id not in arcset[start_reebvert_id]:
					print("Candidate seems to be invalid")
					continue

				arcData = arcset[start_reebvert_id][end_reebvert_id]
				ContourData, ContourIDList =  CreateCentroidsByWalk(candidate, tvmap) # GroupContoursByWalk(arcData.contourData, candidate, tvmap)

				#depending on datagen output, we may switch over to this. After a couple tries it looked pretty good on the torus
				# ContourData, ContourIDList =  CreateBFSBasedCentroidsByWalk(candidate, tvmap) # GroupContoursByWalk(arcData.contourData, candidate, tvmap)
				isDuplicate = False
				#first, start by seeing if we can eliminate any duplicate walks
				for e in edgeChecklist:
					if start_reebvert_id == e[0] and end_reebvert_id == e[1] and e[2]:
						checkContourIDList = e[4]
						if len(checkContourIDList) == len(ContourIDList):
							#perform our match check
							isMatch = True
							for i,c in enumerate(ContourIDList):
								if c != checkContourIDList[i]:
									isMatch = False

							if isMatch:
								isDuplicate = True
								break
							
							#perform our similarity check
							sameCount = 0
							for i,c in enumerate(ContourIDList):
								if c == checkContourIDList[i]: 
									sameCount += 1
							sameRatio = float(sameCount)/float(len(ContourIDList))
							if sameRatio > .875:	#we're basically picking a ratio that is extremely similar
								isDuplicate = True
								break

				#only if we are not a duplicate, carry on with our checks. Note that even here we may not be garaunteed a spot, b/c it's possible we have extraneous walks
				if not isDuplicate:
					for e in edgeChecklist:
						if start_reebvert_id == e[0] and end_reebvert_id == e[1] and not e[2]:
							e[2] = True
							e[3] = ContourData
							e[4] = ContourIDList
							break

			#now at the end of our checklist, for now we want to be sure that ALL edges have been addressed
			allFilled = True
			for e in edgeChecklist:
				allFilled = allFilled and e[2]

			# assert allFilled

			#current conundrum: upon testing the real life data, with noisy input, we actually fail our assertion. A part of me is not surprised, because its possible some edges just dont have any contours to go with them.
			#I may need to temporarily relax this in order to just let the computation proceed, and see what the final result is

			#now that all of our required edges are filled, go over the edges, and put them back in the reeb model
			iso_dist_failure_threshold1 = .35
			for e in edgeChecklist:
				if allFilled or e[2]:
					processedEdges.append([e[0],e[1]])
					for r in reebmodel[1]:
						if e[0] == r[0] and e[1] == r[1] and len(r) == 2:
							for centroid in e[3]:
								debug_centroid_list.append(centroid)
							r.append(e[3])
							break
				else:
					v1 = e[0]
					v2 = e[1]
					i1 = None
					i2 = None
					for v in verts:
						if v[0] == v1:
							i1 = v[1]
						elif v[0] == v2:
							i2 = v[1]
					assert i1 is not None and i2 is not None
					print("failed to add arc for edge (" + str(e[0])+":" + str(i1)+","+str(e[1])+":" + str(i2)+") distance: " + str(abs(i1 - i2)) + " max: " + str(iso_dist_failure_threshold1))
					if abs(i1 - i2) > iso_dist_failure_threshold1:
						print("WARNING: ISO DIST FAILURE THRESHOLD HAS BEEN BREACHED!")


		#now comb through all the reebmodel edges and make sure everything has been supplied
		reebEdgesFilled = True
		for r in reebmodel[1]:
			reebEdgesFilled = reebEdgesFilled and len(r) > 2

		if not reebEdgesFilled:
			print("WARNING: NOT ALL OF THE REEB EDGES ARE FILLED! CHECK OUTPUT TO SEE IF THIS IS ERRONEOUS")
			for r in reebmodel[1]:
				if len(r) == 2:
					r.append([])


		isodistance =  maxiso - miniso
		isointerval = isodistance / float(IsoCount)
		user_isos = []
		for fi in frange(miniso, maxiso, isointerval):
			user_isos.append(fi)
		isodata = CreateIsoLineDataRaw(user_isos, objmodel[0], 3, trilist, funcmodel)
		# isodata = ConvertContourDataToIsoLineRaw(aggregate_contour_data)
		

		#now with the contour data, we need to generate a triangle vert/func based traversal graph
		#as far as traversal goes, I may just do a blind bfs traversal, which should work so long as my edges only go in ascending order (there should be no edges where isovalues are less than the current)

		


		#with the trivert map setup, now parse through each of our reeb model edges, and perform a traversal on them, collecting valid contours along the way
		#put those contours collected into the reeb edge they are associated with. this will be the basis for forming our arcs
		
		reeb_json = {
			"reeb_verts" : reebmodel[0],
			"reeb_edges" : reebmodel[1],
			"max_iso" : maxiso,
			"min_iso" : miniso
			# "debug_centroids" : debug_centroid_list
			# "reeb_edge_arcs" : [],#reeb_edge_arcs,
		}
		iso_json = {
			# "iso_data" : funclist,
			"iso_verts" : isodata[0],
			"iso_lines" : isodata[1],
			"iso_vert_count" : isodata[2],
			# "contour_data" : contourdata,
			# "contour_data": contourdata,
			# "contour_count": len(contourdata),
			"max_iso" : maxiso,
			"min_iso" : miniso
		}
		func_json = {
			"iso_data" : funclist,
			"max_iso" : maxiso,
			"min_iso" : miniso
		}
		#not needed, as the main function already converts the model for us!
		# model_json = {
		# 	"vertices" : vertexlist,
		# 	"faces" : trilist
		# }
		# json.dump(finaljson, objf_json, indent=4)
		# json.dump(reeb_json, reebjson, indent = 4)
		# json.dump(iso_json, isojson, indent = 4)
		# json.dump(func_json, funcjson, indent = 4)
		#attempts to minify json, extract new paths for further processing if needed
	# objfjson_min = minify(OBJFPath)
	# reebjson_min = minify(ReebJSONPath)
	# isojson_min = minify(IsoJSONPath)
	# funcjson_min = minify(FuncJSONPath)

	# json.dump(model_json, modeljson, indent = 4)
	assert func_json is not None and reeb_json is not None and iso_json is not None
	return {"funcs":[func_json, FuncJSONPath], "reeb":[reeb_json, ReebJSONPath], "isolines":[iso_json, IsoJSONPath]}
	

#-----------ALL CONN-GEO RELATED HELPER FUNCTIONS----------------------------------------------
 #returns a list of vertices
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

#returns a list of triangles
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

def convertConnGeoToOBJ(connFilePath,geoFilePath, objFilePath):
	with open(objFilePath,"w") as f:
		#first write the vertices
		for i,p in enumerate(OpenGeometry(geoFilePath)):
			f.write("v "+str(p[0])+" "+str(p[1])+" "+str(p[2])+"\n")
		#then write the tris
		for i,p in enumerate(OpenConnections(connFilePath)):
			f.write("f "+str(p[0])+" "+str(p[1])+" "+str(p[2])+"\n")


#-----------ALL OBJ RELATED HELPER FUNCTIONS----------------------------------------------

def OpenObj(objFilePath):
	vertices = [] #list of vectors
	vertex_normals = []
	tris = []     #list of list of indices
	tri_normal_indices = []
	tri_texture_indices = []
	with open(objFilePath) as f:
		for line in f:
			if line.startswith("vn"):
				parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None,"vn"]] 
				pv = []
				for i,p in enumerate(parts):
					pv.append(float(p))
				vertex_normals.append(pv)
			elif line.startswith("v"):
				parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None,"v"]]
				pv = []
				for i,p in enumerate(parts):
					pv.append(float(p))
				vertices.append(pv)
			elif line.startswith("f"):
				parts = [x.strip() for x in line.split(' ') if not x.isspace() and not x in ['',None,"f"]]
				pv = []
				pvn = []
				pvtexture = []
				for i,p in enumerate(parts):
					#further split into parts to deal with the slashes if any
					containsSlashes = "/" in p
					pparts = []
					if containsSlashes:
						pparts = p.split('/')
						assert len(pparts) == 3
						pvt = int(float(pparts[0])) -1
						pv.append(pvt)
						if pparts[1] != "":
							pvt = int(float(pparts[1])) -1
							pvtexture.append(pvt)
						if pparts[2] != "":
							pvt = int(float(pparts[2])) -1
							pvn.append(pvt)
					else:
						pvt = int(float(p)) -1
						pv.append(pvt)
				tris.append(pv)
				if len(pvn) != 0:
					tri_normal_indices.append(pvn)
				if len(pvtexture) != 0:
					tri_texture_indices.append(pvtexture)
			else:
				print("unable to parse \"" + line + "\"")
				continue
	return (vertices,tris, vertex_normals, tri_normal_indices)

def convertOBJtoConnGeo(objFilePath,connFilePath, geoFilePath):
	objset = OpenObj(objFilePath)
	with open(geoFilePath,"w") as f:
		#first write the vertices
		for i,p in enumerate(objset[0]):
			f.write("   "+str('%e' % p[0])+"   "+str('%e' % p[1])+"   "+str('%e' % p[2])+"\n")
	with open(connFilePath,"w") as f:
		#then write the tris
		for i,p in enumerate(objset[1]):
			f.write("   "+str('%e' % p[0])+"   "+str('%e' % p[1])+"   "+str('%e' % p[2])+"\n")


# go ahead and export our own obj model to json format. Use meshes.vertices and meshes.faces to be consistent with existing webgl code
# assume we have the model data directly to work with
def convertOBJModelToJSON(objModel, objFilePath):
	with open(objFilePath, 'w') as outfile:
		vertexlist = []
		trilist = []
		for i,vert in enumerate(objModel[0]):
			vertexlist.append(vert[0])
			vertexlist.append(vert[1])
			vertexlist.append(vert[2])
		for i,tri in enumerate(objModel[1]):
			trilist.append(tri)
		finaljson = {
			"meshes": [{"vertices": vertexlist, "faces": trilist}]
		}
		json.dump(finaljson, outfile, indent=4)
	outfile_min = minify(objFilePath)

#need to fix the helper structure here!
#apparently our "simplification" isnt handling cycles correctly.. interesting
def ComputeDisjointSet(VertChain, TVMap, iso):
	disjointsets = []
	isCycle = VertChain["isCycle"]
	chains = VertChain["chain"]
	for chain in chains:
		helper = []
		for i, vi in enumerate(chain):
			helper.append([i,vi, TVMap["verts"][vi].iso])
		chainlength = len(chain)
		if not isCycle:
			chainlength -= 1
		for i in range(0, chainlength):
			ith = helper[i]
			jth = helper[(i + 1) % len(helper)]
			isign = math.copysign(1, iso - ith[2])
			jsign = math.copysign(1, iso - jth[2])

			if (isign >= 0 and jsign >= 0) or (isign < 0 and jsign < 0):
				jth[0] = i

		counterset = set()
		counterlist = [] # counter entry: [ancestor_idx, list, direction]

		#probably check here if all of our nodes have the same sign
		first_sign = math.copysign(1, iso - helper[0][2])
		sameSign = True
		for i in range(0, len(chain)):
			if math.copysign(1, iso - helper[i][2]) != first_sign:
				sameSign = False

		if sameSign:
			#we must handle the min or max case
			#in this case, we have it very simple, just get the details of the first vertex, and append everything else to it
			counterset.add(0)
			counterlist.append([0, [], math.copysign(1,  helper[0][2] - iso)])
			for h in helper:
				counterlist[0][1].append(h[1])
		else:
			#we handle the normal case
			for hi, h in enumerate(helper):
				parent = h[0]
				startingpoint = parent
				current = hi
				# print("Starting Parent:  " + str(parent))
				# print("Starting Current: " + str(current))
				#if we loop around, then we know we are a min or max
				while parent != current:
					nextNode = helper[parent]
					current = parent
					parent = nextNode[0]
				ancestor = parent

				if ancestor not in counterset:
					direction = math.copysign(1, helper[parent][2] - iso)
					counterset.add(ancestor)
					counterlist.append([ancestor, [helper[parent][1]], direction])
				else:
					for c in counterlist:
						if c[0] == ancestor:
							c[1].append(h[1])
							break

		for c in counterlist:
			disjointsets.append([c[1], c[2]])
	return disjointsets



def ComputeVertChain(Edgelist, VertNeighborSet):
	graph = dict()
	for e in Edgelist:
		ea, eb = tuple(e)
		if ea not in graph:
			graph[ea] = []
		if eb not in graph:
			graph[eb] = []
		graph[ea].append(eb)
		graph[eb].append(ea)

	seen = set()
	outputChain = []
	isCycle = True

	for k in graph.keys():
		if len(graph[k]) == 1:
			isCycle = False
			break

	for k in graph.keys():
		if k in seen or (len(graph[k]) != 1 and not isCycle): continue
		stack = [k]
		stackChanged = True
		while stackChanged:
			stackChanged = False
			top = stack[-1]
			seen.add(top)
			neighbors = graph[top]
			for n in neighbors:
				if n not in seen:
					stack.append(n)
					stackChanged = True
					break
		outputChain.append(stack)
	assert len(seen) == len(VertNeighborSet)
	return {"chain" : outputChain, "isCycle": isCycle, "disjointSet": None, "minpaths":[], "maxpaths":[]}


def CreateVertMap(vertcount, trilist, vertlist):
	vertmap = dict()
	for tri in trilist:
		verta = tri[0]
		vertb = tri[1]
		vertc = tri[2]
		for vi in [verta,vertb,vertc]:
			if vi not in vertmap:
				vertmap[vi] = {"id":vi, "pos": vertlist[vi], "neighbors": []}

		for vi in [verta,vertb,vertc]:
			newlist = set([verta,vertb,vertc])
			newlist.remove(vi)
			newlist = list(newlist)
			for vj in newlist:
				if vi not in vertmap[vj]["neighbors"]:
					vertmap[vj]["neighbors"].append(vi)


	return vertmap



#current status:
#apparently the reeb arc traversals are miserably failing, as we do not seem to reach the end at all!
#as such, all of our arcs just return with empty data
#this is unacceptable
#todo
# TVData = recordtype('TVData', 'min_vid max_vid min_iso max_iso iso neighbors_trilist trilist')
#we may have to resort to a much slower method, which is to manually store all iso values with each neighbor
#and then always select the max from them
#i think I need to setup the neighbor lookup such that we always look for the max value such that it never exceeds the iso value of our target point (that way we can't veer off)
def CreateTVMap(vertcount, funclist, trilist, vertlist): #i dont think i need vertex list
	TVMap = {"verts": dict(), "tris": dict(), "pos2vert_octree": None}
	#first pass
	for tid, tri in enumerate(trilist):
		verta = tri[0]
		vertb = tri[1]
		vertc = tri[2]
		ia = funclist[verta]
		ib = funclist[vertb]
		ic = funclist[vertc]

		#process tri first
		if tid not in TVMap["tris"]:
			TVMap["tris"][tid] = TriData(va = verta, vb = vertb, vc = vertc, \
										minIso = min([ia,ib,ic]), maxIso = max([ia,ib,ic]),\
										triNeighbors = [])

		#now process verts, first check if they are registered
		for v_i_pair in [(verta, ia), (vertb, ib), (vertc, ic)]:
			v, isop = v_i_pair
			if v not in TVMap["verts"]:
				TVMap["verts"][v] = VertData(vid = v, vpos = vertlist[v], neighborEdgelist = [], vertNeighborTriMap = dict(), \
											 vertNeighbors = set(), triNeighbors = set(), iso = isop,\
											 vertNeighborChain = None)

		#process verts
		for v in [verta, vertb, vertc]:
			otherset = set([verta, vertb, vertc])
			otherset.remove(v)
			vx, vy = tuple(list(otherset))
			vertex = TVMap["verts"][v]
			vertex.neighborEdgelist.append(sorted([vx, vy]))
			vertex.vertNeighbors.add(vx)
			vertex.vertNeighbors.add(vy)
			vertex.triNeighbors.add(tid)

			if vx not in vertex.vertNeighborTriMap:
				vertex.vertNeighborTriMap[vx] = set()

			if vy not in vertex.vertNeighborTriMap:
				vertex.vertNeighborTriMap[vy] = set()

			vertex.vertNeighborTriMap[vx].add(tid)
			vertex.vertNeighborTriMap[vy].add(tid)

	#second pass: solve neighbor tris
	for tid, tri in enumerate(trilist):
		for i, vi in enumerate([tri[0], tri[1], tri[2]]):
			vj = [tri[0], tri[1], tri[2]][(i + 1) % 3]
			i_tris = TVMap["verts"][vi].triNeighbors
			j_tris = TVMap["verts"][vj].triNeighbors

			matches = []
			for t in list(i_tris):
				if t in j_tris and t != tid:
					matches.append(t)
					break
			if len(matches) > 0:
				TVMap["tris"][tid].triNeighbors.append(matches[0])

	#third pass: solve for neighbor chains
	for vid in range(0, vertcount):
		vertex = TVMap["verts"][vid]
		vertChain = ComputeVertChain(vertex.neighborEdgelist, vertex.vertNeighbors)
		vertex.vertNeighborChain = vertChain
		disjointset = ComputeDisjointSet(vertChain, TVMap, vertex.iso)
			
		vertex.vertNeighborChain["disjointSet"] = disjointset
		for dset in disjointset:
			helper = []
			for si in dset[0]:
				helper.append([si, TVMap["verts"][si].iso])
			
			for h in helper:
				if h[1] >= vertex.iso:
					value = max(helper, key = lambda f: f[1]) [0]
					if value not in vertex.vertNeighborChain["maxpaths"]:
						vertex.vertNeighborChain["maxpaths"].append(value)
				else:
					value = min(helper, key = lambda f: f[1]) [0]
					if value not in vertex.vertNeighborChain["minpaths"]:
						vertex.vertNeighborChain["minpaths"].append(value)

		# if vid == 7:
		# 	pp = pprint.PrettyPrinter(indent = 3)
		# 	# pp.pprint(disjointset)
		# 	pp.pprint(vertex.vertNeighborChain)
		# 	raise Exception
		

	return TVMap


def CreateTriangleBands(VertID, TargetIso, TVMap):
	# print(VertID)
	vertex = TVMap["verts"][VertID]
	min_paths = len(vertex.vertNeighborChain["minpaths"])
	max_paths = len(vertex.vertNeighborChain["maxpaths"])
	triangle_band = set()
	type = ""
	if  min_paths == 1 and  max_paths == 1:
		# print(VertID)
		# print("ERROR! THIS IS SUPPOSED TO BE FOR REEB VERTICES! NOT REGULAR VERTICES IN THE MESH!")
		# raise Exception
		print("WARNING! MAKING A SADDLE BAND BASED OFF OF A REGULAR VERTEX! PLEASE VERIFY MESH INPUT AND REEB GRAPH IF THIS IS ACCEPTABLE")
		print("DESIGNATING THIS AS A SPECIAL CASE SADDLE")
		type = "saddle"
		starting_tri_list = list(vertex.triNeighbors)
		q = []
		seen_tris = set()
		for t in starting_tri_list:
			q.append(t)
			triangle_band.add(t)
			seen_tris.add(t)

		while len(q) != 0:
			current_tri = TVMap["tris"][q.pop(0)]
			neighbors = current_tri.triNeighbors
			for n in neighbors:
				n_tri = TVMap["tris"][n]
				if TargetIso >= n_tri.minIso and TargetIso <= n_tri.maxIso and n not in seen_tris:
					triangle_band.add(n)
					q.append(n)
					seen_tris.add(n)

	elif min_paths == 0 and max_paths == 0:
		print("ERROR! MALFORMED VERTEX DETECTED!")
		raise Exception
	elif min_paths == 0 and max_paths > 0:
		#this is the minima
		type = "min"
		triangle_band = set(vertex.triNeighbors)
	elif min_paths > 0 and max_paths == 0:
		#this is the maxima
		type = "max"
		triangle_band = set(vertex.triNeighbors)
	else:
		#we are in the saddle
		type = "saddle"
		#now we have to do something a little more complicated
		starting_tri_list = list(vertex.triNeighbors)
		q = []
		seen_tris = set()
		for t in starting_tri_list:
			q.append(t)
			triangle_band.add(t)
			seen_tris.add(t)

		#now we need to also perform triangle traversal. use bfs to do this
		while len(q) != 0:
			# if VertID == 15:
			# 	print(q)
			current_tri = TVMap["tris"][q.pop(0)]
			neighbors = current_tri.triNeighbors
			for n in neighbors:
				n_tri = TVMap["tris"][n]
				if TargetIso >= n_tri.minIso and TargetIso <= n_tri.maxIso and n not in seen_tris:
					triangle_band.add(n)
					q.append(n)
					seen_tris.add(n)

	min_Iso = TargetIso
	max_Iso = TargetIso
	for t in list(triangle_band):
		tri = TVMap["tris"][t]
		if tri.minIso < min_Iso: min_Iso = tri.minIso
		if tri.maxIso > max_Iso: max_Iso = tri.maxIso

	return TriBand(vertID=VertID, targetIso=TargetIso, maxIso=max_Iso, minIso=min_Iso, vertType=type, triangleBandSet=triangle_band, edgeList = [])

# TriData = recordtype('TriData', 'va vb vc minIso maxIso triNeighbors')
# VertData = recordtype('VertData', 'vid vpos vertNeighbors triNeighbors iso vertNeighborChain vertNeighborTriMap neighborEdgelist')
#a pair of 2 vertices [[x,y,z] [x,y,z]] is returned
def GetIsoLineFromTri(iso, tid, TVMap):
	tri = TVMap["tris"][tid]
	v1i = tri.va
	v2i = tri.vb
	v3i = tri.vc

	i1 = TVMap["verts"][v1i].iso
	i2 = TVMap["verts"][v2i].iso
	i3 = TVMap["verts"][v3i].iso


	#now determine our two iso segment points 
	# xxx = v1, v2, v3, 0 = below, 1 = above
	iv1 = None
	iv2 = None
	#if we dont have iso anywhere near us, ignore this iteration
	# 000
	if i1 <= iso and i2 <= iso and i3 <= iso:
		return []
	# 111
	if i1 > iso and i2 > iso and i3 > iso:
		return []


	#therefore, ive changed vertex list to instead use an array of arrays for easier indexing
	v1 = TVMap["verts"][v1i].vpos
	v2 = TVMap["verts"][v2i].vpos
	v3 = TVMap["verts"][v3i].vpos

	# assume counter clockise rotation
	# vert order:
	# 123


	# 3 cases for one point below the iso value
	# 011
	if i1 <= iso and i2 > iso and i3 > iso:
		iv1 = map_iso(iso, i1, i2, v1, v2)
		iv2 = map_iso(iso, i1, i3, v1, v3)
		# print("011")
		
	# 101
	elif i1 > iso and i2 <= iso and i3 > iso:
		# print("101")
		iv1 = map_iso(iso, i2, i3, v2, v3)
		iv2 = map_iso(iso, i2, i1, v2, v1)
		
	# 110
	elif i1 > iso and i2 > iso and i3 <= iso:
		
		# print("110")
		iv1 = map_iso(iso, i3, i2, v3, v2)
		iv2 = map_iso(iso, i3, i1, v3, v1)
		

	# 3 cases for one point above the iso value
	# 100
	elif i1 > iso and i2 <= iso and i3 <= iso:
		# print("100")
		iv1 = map_iso(iso, i3, i1, v3, v1)
		iv2 = map_iso(iso, i2, i1, v2, v1)
		
	# 010
	elif i1 <= iso and i2 > iso and i3 <= iso:
		# print("010")
		iv1 = map_iso(iso, i1, i2, v1, v2)
		iv2 = map_iso(iso, i3, i2, v3, v2)
		
	# 001
	elif i1 <= iso and i2 <= iso and i3 > iso:
		# print("001")
		iv1 = map_iso(iso, i2, i3, v2, v3)
		iv2 = map_iso(iso, i1, i3, v1, v3)
		
	assert iv1 is not None and iv2 is not None
	
	return [iv1, iv2]

#a simpler version of triangle band, as we have no need to concern ourselves with edge cases regarding CPs
def CreateContourCentroid(VertID, TargetIso, TVMap):
	vertex = TVMap["verts"][VertID]
	min_paths = len(vertex.vertNeighborChain["minpaths"])
	max_paths = len(vertex.vertNeighborChain["maxpaths"])
	triangle_band = set()
	starting_tri_list = list(vertex.triNeighbors)
	q = []
	seen_tris = set()
	for t in starting_tri_list:
		q.append(t)
		triangle_band.add(t)
		seen_tris.add(t)
	while len(q) != 0:
		current_tri = TVMap["tris"][q.pop(0)]
		neighbors = current_tri.triNeighbors
		for n in neighbors:
			n_tri = TVMap["tris"][n]
			if TargetIso >= n_tri.minIso and TargetIso <= n_tri.maxIso and n not in seen_tris:
				triangle_band.add(n)
				q.append(n)
				seen_tris.add(n)
	line_list = []
	#now take our tris, and get the line list from them
	for tri in list(triangle_band):
		til = GetIsoLineFromTri(TargetIso, tri, TVMap)
		if len(til) != 0:
			line_list.append(til[0])
			line_list.append(til[1])

	if len(line_list) == 0:
		return []
	centroid = [0.0,0.0,0.0]
	for l in line_list:
		centroid[0] += l[0]
		centroid[1] += l[1]
		centroid[2] += l[2]
	
	centroid = [centroid[0] / float(len(line_list)), centroid[1] / float(len(line_list)), centroid[2] / float(len(line_list))]
	return centroid

#return a single instance of [start_reeb_id, end_reeb_id, walk_history = [vertid, ...]]
def StupidReebWalkBFS(startReebID, endReebID, VertMap):
	#schema: [topid, walk_history]
	q = [ [startReebID, [] ] ]
	
	result = []
	seen_verts = set()
	seen_verts.add(startReebID)
	while len(q) != 0:
		curid, walk_history = tuple(q.pop(0))
		curvert = VertMap[curid]
		neighbor_ids = curvert["neighbors"]
		# print("CurID: " + str(curid)+ " Neighbors: " + str(neighbor_ids))
		for nid in neighbor_ids:
			#if our neighbor is our target vertex, exit now!
			if nid == endReebID:
				result = [startReebID, endReebID, walk_history]
				break
			else:
				#we continue propagation if we are not seen before
				if nid not in seen_verts:
					seen_verts.add(nid)
					q.append([nid, walk_history + [nid]])
		if len(result) != 0:
			break

	return result

def StupidReebWalkBFSMultiple(startReebID, endReebID, VertMap, target = 1):
	q = [ [startReebID, [] ] ]
	
	results = []
	seen_verts = set()
	seen_verts.add(startReebID)
	while len(q) != 0:
		curid, walk_history = tuple(q.pop(0))
		curvert = VertMap[curid]
		neighbor_ids = curvert["neighbors"]
		# print("CurID: " + str(curid)+ " Neighbors: " + str(neighbor_ids))
		for nid in neighbor_ids:
			#if our neighbor is our target vertex, exit now!
			if nid == endReebID:
				results.append([startReebID, endReebID, walk_history])
				break
			else:
				#we continue propagation if we are not seen before
				if nid not in seen_verts:
					seen_verts.add(nid)
					q.append([nid, walk_history + [nid]])
		if len(result) == target:
			break

	return result

#return a list of [ [start_reeb_id, end_reeb_id, walk_history = [vertid, ...]], ...]
def ReebWalkerBFS(TriangleBands, TVMap, VertexObject, BandObject, ProcessedEdges):
	vertChain = VertexObject.vertNeighborChain
	# pp = pprint.PrettyPrinter(indent = 3)
	# pp.pprint(vertChain)
	# if BandObject.vertID == 19:
	# 	print(vertChain)
	maxpaths = vertChain["maxpaths"]
	q = []
	result_paths = []
	start_reeb_id = BandObject.vertID
	seen_verts = set()
	bandverts = set()
	for t in TriangleBands:
		bandverts.add(t.vertID)
	for startID in maxpaths:
		end_reeb_id = -1
		walk_history = [startID]
		triband_current_vert = -1
		triband_iso = float('inf')
		q.append([startID, walk_history, triband_current_vert, triband_iso])

	while len(q) != 0:
		current = tuple(q.pop(0))
		top, walk_history, triband_current_vert, triband_iso = current
		topvert = TVMap["verts"][top]
		neighbor_ids = topvert.vertNeighborChain["maxpaths"]
		

		#here we declare the victory condition, which will kill this branch of execution
		if len(walk_history) != 0 and top in bandverts:
			end_reeb_id = top
			result_paths.append([start_reeb_id, end_reeb_id, walk_history])
		else:
			#now we begin path propagation

			#first check to see if we are in a triangle band, or a new one, in case
			for tb in TriangleBands:
				if tb.vertID == BandObject.vertID: continue
				for t in list(topvert.triNeighbors):
					#now to handle some really specific corner cases, we need to perform a backedge detection
					if t in tb.triangleBandSet and tb.targetIso < triband_iso and tb.vertID != BandObject.vertID:
						backEdgeDetected = False
						for pe in ProcessedEdges:
							if start_reeb_id == pe[1] and tb.vertID == pe[0]:
								print("BACKEDGE DETECTED!")
								backEdgeDetected = True
								break

						if not backEdgeDetected:
							triband_current_vert = tb.vertID
							triband_iso = tb.targetIso
						break

			#now if we are in a triangle band, see if our iso value has exceeded it, if so, we can exit
			# in this case, we just simply push back this frame onto the queue
			if triband_current_vert != -1 and topvert.iso >= triband_iso:
				q.append([triband_current_vert, walk_history, triband_current_vert, triband_iso])
			else:
				#otherwise we continue with traversal. due to BFS, this is propagation, not just simple traversal
				#in the event nothing is chosen... due to BFS our current path will just die
				for nid in neighbor_ids:
					if nid not in seen_verts:
						seen_verts.add(nid)
						new_walk = walk_history
						new_walk.append(nid)
						q.append([nid, new_walk, triband_current_vert, triband_iso])
	return result_paths



#return a list of [ [start_reeb_id, end_reeb_id, walk_history = [vertid, ...]], ...]
def ReebWalker(TriangleBands, TVMap, VertexObject, BandObject, ProcessedEdges):
	vertChain = VertexObject.vertNeighborChain
	# pp = pprint.PrettyPrinter(indent = 3)
	# pp.pprint(vertChain)
	# if BandObject.vertID == 19:
	# 	print(vertChain)
	maxpaths = vertChain["maxpaths"]
	walks = []
	start_reeb_id = BandObject.vertID
	for startID in maxpaths:
		end_reeb_id = -1
		walk_history = [startID]
		bandverts = set()
		for t in TriangleBands:
			bandverts.add(t.vertID)
		top = walk_history[-1]
		seen_verts = set()
		triband_current_vert = -1
		triband_iso = float('inf')
		while top not in bandverts and len(walk_history) != 0:
			top = walk_history[-1]
			topvert = TVMap["verts"][top]
			neighbor_ids = topvert.vertNeighborChain["maxpaths"]
			chosen_id = -1

			
			
			#first check to see if we are in a triangle band, or a new one, in case
			for tb in TriangleBands:
				if tb.vertID == BandObject.vertID: continue
				for t in list(topvert.triNeighbors):
					if t in tb.triangleBandSet and tb.targetIso < triband_iso and tb.vertID != BandObject.vertID:
						#now to handle some really specific corner cases, we need to perform a backedge detection
						backEdgeDetected = False
						for pe in ProcessedEdges:
							if start_reeb_id == pe[1] and tb.vertID == pe[0]:
								print("BACKEDGE DETECTED!")
								backEdgeDetected = True
								break

						if not backEdgeDetected:
							triband_current_vert = tb.vertID
							triband_iso = tb.targetIso
						break

			#now if we are in a triangle band, see if our iso value has exceeded it, if so, we can exit
			if triband_current_vert != -1 and topvert.iso >= triband_iso:
				top = triband_current_vert
				continue

			#otherwise we continue with traversal
			for nid in neighbor_ids:
				if nid not in seen_verts:
					seen_verts.add(nid)
					chosen_id = nid
					break

			if chosen_id == -1:
				print("WE ARE BACKTRACKING! ReebVert("+ str(BandObject.vertID)+") TopVert: " + str(top))
				#we need to backtrack, as weve reached a deadend
				walk_history.pop(-1)
				continue
			else:
				walk_history.append(chosen_id)
		#if our walk was successful, append a new entry
		if len(walk_history) != 0 and top in bandverts:
			end_reeb_id = top
			walks.append([start_reeb_id, end_reeb_id, walk_history])

	
	return walks



# reeb walk is defined as [startid, endid, walk_history = [id, id, ...]]
def GroupContoursByWalk(ContourData, ReebWalk, TVMap):
	start_reeb_id = ReebWalk[0]
	end_reeb_id = ReebWalk[1]
	walk_history = ReebWalk[2]
	contour_list = []

	full_walk = [start_reeb_id]
	for w in walk_history:
		full_walk.append(w)
	full_walk.append(end_reeb_id)

	for w in full_walk:
		vert = TVMap["verts"][w]
		seen_contour_ids = set()
		verttris = list(vert.triNeighbors)
		for con in ContourData:
			con_tri_set = set(con["contour"]["tri_set"])
			for vt in verttris:
				if vt in con_tri_set:
					if con["id"] not in seen_contour_ids:
						seen_contour_ids.add(con["id"])
						centroid = con["contour"]["centroid"]
						iso = con["iso_level"]
						id = con["id"]
						contour_list.append([centroid[0], centroid[1], centroid[2], iso, id])
					break

	contour_list.sort(key = lambda f: f[3]) #sort by isovalue if needed
	final_contour_list = []
	final_contour_id_list = []

	for con in contour_list:
		final_contour_list.append([con[0], con[1], con[2], con[3]])
		final_contour_id_list.append(con[4])
	return (final_contour_list, final_contour_id_list)

#CreateContourCentroid(VertID, TargetIso, TVMap)
#note: in this case, we have to base our centroids off of the length of the geometry, not the iso distance
# for every n walks, we produce the centroid, known as the walk centroid rate
def CreateCentroidsByWalk(ReebWalk, TVMap, WalkCentroidRate = 12):
	start_reeb_id = ReebWalk[0]
	end_reeb_id = ReebWalk[1]
	walk_history = ReebWalk[2]
	print("Length of walk: " + str(len(walk_history)))
	contour_list = []

	start_iso = TVMap["verts"][start_reeb_id].iso
	end_iso = TVMap["verts"][end_reeb_id].iso
	# print("-------------------------------------sdfsdfdsfdsfsdfs--------------------------------------------")
	#actually, lets just make wcr 1 and see what happens
	wcr = 1 #len(walk_history) / WalkCentroidRate


	full_walk = [start_reeb_id]
	for w in walk_history:
		full_walk.append(w)
	full_walk.append(end_reeb_id)

	intervalGauge = wcr
	last_vert_id = start_reeb_id
	for w in full_walk:
		if w != start_reeb_id:
			vert = TVMap["verts"][w]
			last_vert = TVMap["verts"][last_vert_id]
			intervalGauge -= 1
			if intervalGauge <= 0:
				target_iso = (vert.iso + last_vert.iso)/2.0
				centroid = CreateContourCentroid(w, target_iso, TVMap)
				intervalGauge = wcr
				if len(centroid) != 0:
					contour_list.append([centroid[0],centroid[1],centroid[2], target_iso, -1]) #b/c we are generating contours on the fly, we do not refer to a contour id, thus -1
				else:
					print("Failed to get iso contour")
		last_vert_id = w

	contour_list.sort(key = lambda f: f[3]) #sort by isovalue if needed
	final_contour_list = []
	final_contour_id_list = []
	print("Contour List Length: "+str(len(contour_list)))
	assert len(contour_list) != 0

	for con in contour_list:
		final_contour_list.append([con[0], con[1], con[2], con[3]])
		final_contour_id_list.append(con[4])
	return (final_contour_list, final_contour_id_list)

#what this simply means is that we will pass off the vertices themselves as the 'centroids'
def CreateBFSBasedCentroidsByWalk(ReebWalk, TVMap):
	start_reeb_id = ReebWalk[0]
	end_reeb_id = ReebWalk[1]
	walk_history = ReebWalk[2]
	print("Length of walk: " + str(len(walk_history)))
	contour_list = []

	start_iso = TVMap["verts"][start_reeb_id].iso
	end_iso = TVMap["verts"][end_reeb_id].iso
	# print("-------------------------------------sdfsdfdsfdsfsdfs--------------------------------------------")
	#actually, lets just make wcr 1 and see what happens
	wcr = 1 #len(walk_history) / WalkCentroidRate


	full_walk = [start_reeb_id]
	for w in walk_history:
		full_walk.append(w)
	full_walk.append(end_reeb_id)

	intervalGauge = wcr
	last_vert_id = start_reeb_id
	for w in full_walk:
		if w != start_reeb_id:
			vert = TVMap["verts"][w]
			last_vert = TVMap["verts"][last_vert_id]
			intervalGauge -= 1
			if intervalGauge <= 0:
				# target_iso = (vert.iso + last_vert.iso)/2.0
				target_iso = vert.iso
				centroid = vert.vpos
				intervalGauge = wcr
				contour_list.append([centroid[0],centroid[1],centroid[2], target_iso, -1]) #b/c we are generating contours on the fly, we do not refer to a contour id, thus -1
		last_vert_id = w

	contour_list.sort(key = lambda f: f[3]) #sort by isovalue if needed
	final_contour_list = []
	final_contour_id_list = []
	print("Contour List Length: "+str(len(contour_list)))
	assert len(contour_list) != 0

	for con in contour_list:
		final_contour_list.append([con[0], con[1], con[2], con[3]])
		final_contour_id_list.append(con[4])
	return (final_contour_list, final_contour_id_list)

def GroupContoursByWalker33(ContourData, TVMap, ReebStartVert, startIso, ReebEndVert, endIso):
	reebstart = TVMap["verts"][ReebStartVert]
	reebend = TVMap["verts"][ReebEndVert]

	#big assumption: we assume all starting paths are valid, and sufficient and necessary
	walkerpaths = reebstart.vertNeighborChain["maxpaths"]
	pp = pprint.PrettyPrinter(indent = 3)
	# if ReebStartVert == 19:
	# 	pp.pprint(reebstart.vertNeighborChain)
	# 	print(ReebStartVert)
	print("Length of the walker paths: " + str(len(walkerpaths)))
	print(ReebStartVert)
	print(ReebEndVert)
	selected_contours = []
	walk_histories = []
	seen_contour_paths = []
	for walk_start in walkerpaths:
		print("-----STARTING WALK!------ GOAL VERT: "+str(ReebEndVert)+" GOAL ISO: "+str(endIso))
		walkerstate = [walk_start, TVMap["verts"][walk_start].iso]
		centroid_list = []
		seenverts = set()
		seencontours = set()
		walkhistory = []
		while walkerstate[0] != ReebEndVert and walkerstate[1] < endIso:
			current_id, current_iso = tuple(walkerstate)
			current_tris = list(TVMap["verts"][current_id].triNeighbors)
			walkhistory.append(current_id)
			for con in ContourData:
				id = con["id"]
				iso = con["iso_level"]
				centroid = con["contour"]["centroid"]
				con_tris = set(con["contour"]["tri_set"])
				intersecting = False
				
				for t in current_tris:
					# print(t)
					if t in con_tris:
						intersecting = True
						break
				if intersecting and id not in seencontours:
					centroid_list.append([centroid[0], centroid[1], centroid[2], iso, id])
					seencontours.add(id)
			seenverts.add(current_id)
			next = -1
			# if ReebStartVert == 19:
			# 	pp.pprint(TVMap["verts"][current_id].vertNeighborChain)
			# 	print("from:")
			# 	pp.pprint(walkerstate)
			for n in TVMap["verts"][current_id].vertNeighborChain["maxpaths"]:
				n_iso = TVMap["verts"][n].iso
				if n not in seenverts:
					next = n
					break
			#if we fail to find our next vertex, we are stuck and have to exit... 
			#this might be okay, but for now I want to raise an exception to see if we ever reach this case
			if next == -1:
				print("COULD NOT CONTINUE REEB WALK!")
				raise Exception

			next_iso = TVMap["verts"][next].iso
			walkerstate = [next, next_iso]
			# if ReebStartVert == 19:
			# 	print("to: ")
			# 	pp.pprint(walkerstate)

		if ReebStartVert == 19:
			pp.pprint(TVMap["verts"][walkerstate[0]])
		if walkerstate[0] not in walkhistory:
			walkhistory.append(walkerstate[0])

		centroid_list.sort(key = lambda f: f[3]) # sort by iso level just in case
		#now check to see if we have a new walk, or an old one
		newWalk = True
		visited_contours = []
		for c in centroid_list:
			visited_contours.append(c[4])

		#first check if we can absolutely eliminate any candidates
		for path in seen_contour_paths:
			if len(path) != len(visited_contours): continue
			allSame = True
			for i,p in enumerate(path):
				if p != visited_contours[i]: 
					allSame = False
					break
			
			if allSame: 
				newWalk = False
				break

		#now we instead check to see if they are very similar
		if newWalk:
			for path in seen_contour_paths:
				if len(path) != len(visited_contours): continue
				sameCount = 0
				for i,p in enumerate(path):
					if p== visited_contours[i]:
						sameCount += 1
				sameRatio = float(sameCount)/ float(len(path))
				# print(sameRatio)
				#In the long run, I dont know how good an idea this is, b/c we might overprune if we're too sensitive
				if sameRatio >= .875:
					newWalk = False
					break

		#if we survive all of the checks, add it to our selected walks
		if newWalk:
			selected_contours.append(centroid_list)
			seen_contour_paths.append(visited_contours)
			walk_histories.append(walkhistory)
	
	#so for whatever reason, we have contours being selected that have the same routes, despite different paths there
	#we can do a final scan and only select paths that are different
	# if ReebStartVert == 19:
	# 	pp.pprint(seen_contour_paths)
	# 	pp.pprint(walk_histories)
	return selected_contours



def CreateMeshComponents(VertexList, FuncList, TriList, MinIso, MaxIso, ReebStartVert, ReebEndVert, Epsilon):
	tvmap = {"valid-verts": dict(), "invalid-verts": set(), "invalid-tris": set(),\
			 "reeb-start": {"id": ReebStartVert, "triset": set(), "vertset":set(), "disjoint_neighbors":[]},\
			 "reeb-end": {"id": ReebEndVert, "triset": set(), "vertset":set(), "disjoint_neighbors":[]}}
	print(str(MinIso) + "->" + str(MaxIso))
	for ti, tri in enumerate(TriList):
		v1,v2,v3 = tuple(tri)
		i1 = FuncList[v1]
		i2 = FuncList[v2]
		i3 = FuncList[v3]

		#init if necessary
		for vt in [v1,v2,v3]:
			if vt not in tvmap["valid-verts"] and vt not in tvmap["invalid-verts"]:
				it = FuncList[vt]
				if it > MinIso and it < MaxIso:
					tvmap["valid-verts"][vt] = TVData(iso = it, trilist = [], neighbors_trilist = dict(), \
												  maxvert = {"id": -1, "iso": float("-inf")}, component_id = -1)
				else:
					tvmap["invalid-verts"].add(vt)

		for vi in [v1,v2,v3]:
			remainder_list = [v1,v2,v3]
			remainder_list.remove(vi)
			vj, vk = tuple(remainder_list)

			#if we have one valid vert, we can consider the current triangle
			if vi in tvmap["valid-verts"] or vj in tvmap["valid-verts"] or vk in tvmap["valid-verts"]:
				if vi in tvmap["valid-verts"]:
					if ti not in tvmap["valid-verts"][vi].trilist:
						# tvmap["valid-verts"][vt].trilist.append(ti)
						tvmap["valid-verts"][vi].trilist.append(ti)
			else:
				tvmap["invalid-tris"].add(ti)

			if vi in tvmap["invalid-verts"]: continue

			for vt in [vj, vk]:
				if vt in tvmap["invalid-verts"]: continue

				if vi in tvmap["valid-verts"] and vt not in tvmap["valid-verts"][vi].neighbors_trilist:
					tvmap["valid-verts"][vi].neighbors_trilist[vt] = []
				if vt in tvmap["valid-verts"] and vi not in tvmap["valid-verts"][vt].neighbors_trilist:
					tvmap["valid-verts"][vt].neighbors_trilist[vi] = []

				it = FuncList[vt]
				
				if it <= (MinIso + Epsilon) or it >= (MaxIso - Epsilon): continue
				#now add the triangle to each link
				if vi in tvmap["valid-verts"] and vt in tvmap["valid-verts"] and ti not in tvmap["invalid-tris"]:
					if tvmap["valid-verts"][vi].maxvert["iso"] < it: tvmap["valid-verts"][vi].maxvert = {"iso":it,"id":vt}
					if ti not in tvmap["valid-verts"][vi].neighbors_trilist[vt]:
						tvmap["valid-verts"][vi].neighbors_trilist[vt].append(ti)
					if ti not in tvmap["valid-verts"][vt].neighbors_trilist[vi]:
						tvmap["valid-verts"][vt].neighbors_trilist[vi].append(ti)

		
		#provide a special case for reeb end points
		for vt in [v1,v2,v3]:
			if vt == ReebStartVert:
				tvmap["reeb-start"]["triset"].add(ti)
				if v1 in tvmap["valid-verts"] and vt != v1:
					tvmap["reeb-start"]["vertset"].add(v1)
				if v2 in tvmap["valid-verts"] and vt != v2:
					tvmap["reeb-start"]["vertset"].add(v2)
				if v3 in tvmap["valid-verts"] and vt != v3:
					tvmap["reeb-start"]["vertset"].add(v3)

			elif vt == ReebEndVert:
				tvmap["reeb-end"]["triset"].add(ti)
				if v1 in tvmap["valid-verts"] and vt != v1:
					tvmap["reeb-end"]["vertset"].add(v1)
				if v2 in tvmap["valid-verts"] and vt != v2:
					tvmap["reeb-end"]["vertset"].add(v2)
				if v3 in tvmap["valid-verts"] and vt != v3:
					tvmap["reeb-end"]["vertset"].add(v3)


	reebstartconnected = False
	reebendconnected = False

	for tri in list(tvmap["reeb-start"]["triset"]):
		reebstartconnected = tri not in tvmap["invalid-tris"] or reebstartconnected
	for tri in list(tvmap["reeb-end"]["triset"]):
		reebendconnected = tri not in tvmap["invalid-tris"] or reebendconnected

	if not (reebstartconnected and reebendconnected):
		print("FAILURE: COULD NOT ESTABLISH REEB CONNECTION IN MESH! Arc Edge Info: "+ str(ReebStartVert) +" "+ str(ReebEndVert))
		return [], tvmap

	components = []
	vertcount = len(VertexList)

	for vi in range(0, vertcount):
		if vi in tvmap["invalid-verts"]: continue
		if tvmap["valid-verts"][vi].component_id != -1: continue

		q = queue.Queue()
		newcomponent = Component(id= len(components), vertset=set(), triset=set())
		newcomponent.vertset.add(vi)
		q.put(vi)
		while not q.empty():
			vc = q.get()
			tvmap["valid-verts"][vc].component_id = len(components)
			for t in tvmap["valid-verts"][vc].trilist:
				newcomponent.triset.add(t)
			for k in tvmap["valid-verts"][vc].neighbors_trilist.keys():
				for t in tvmap["valid-verts"][vc].neighbors_trilist[k]:
					newcomponent.triset.add(t)
			# newcomponent.vertset.add(vc)
			for k in tvmap["valid-verts"][vc].neighbors_trilist.keys():
				if k not in newcomponent.vertset:
					q.put(k)
					newcomponent.vertset.add(k)
		components.append(newcomponent)

	reebstartvertlist = set()
	reebendvertlist = set()

	for ti in list(tvmap["reeb-start"]["triset"]):
		v1,v2,v3 = tuple(TriList[ti])
		reebstartvertlist.add(v1)
		reebstartvertlist.add(v2)
		reebstartvertlist.add(v3)

	for ti in list(tvmap["reeb-end"]["triset"]):
		v1,v2,v3 = tuple(TriList[ti])
		reebendvertlist.add(v1)
		reebendvertlist.add(v2)
		reebendvertlist.add(v3)

	for c in components:
		contained = False
		newset = reebstartvertlist.union(reebendvertlist)
		for v in list(newset):
			if v in c.vertset: contained = True
		if not contained: c.id = -1

	finalcomponents = []
	for c in components:
		if c.id != -1: finalcomponents.append(c)

	return finalcomponents, tvmap


#now we need to change our group contours to instead perform partial reeb walking along the component mesh
#hopefully this is captured by the tvmap itself, as it's created in the mesh component function
#the idea is as follows:
#  take each vertex, and attempt to walk along it, and collect any contours along the way. If and only if the walks are successful do we claim the contours for that walk. otherwise nothing happens. this is to account for dead ends
#  if a walk runs into an already claimed contour, then it's retreading the same steps and we ignore it (potential question: what if it finds contours but then runs into an already claimed one? do we have a partial new path?)
def GroupContours1(ContourData, Components, ReebStartVert, ReebEndVert, MinIso, MaxIso, Epsilon, TVMap):
	component_contour_set = dict()
	#todo: create an ignore contour set, and add to it all contours whose triangles are shared with the start and end reeb verts
	#      this way we can prune any obvious collision points
	contour_ignore_set = set()

	#prune all obvious contours causing confusion
	for c in ContourData:
		for tri in TVMap["reeb-start"]["triset"]:
			if tri in c["contour"]["tri_set"]:
				contour_ignore_set.add(c["id"])
				break
		if c["id"] not in contour_ignore_set:
			for tri in TVMap["reeb-end"]["triset"]:
				if tri in c["contour"]["tri_set"]:
					contour_ignore_set.add(c["id"])
					break
	walklists = []
	contourlistlist = []
	pp = pprint.PrettyPrinter(indent = 4)
	
	# print(len(ContourData))
	# for c in ContourData:
	# 	print(c["id"])
	for rv in list(TVMap["reeb-start"]["vertset"]):
		#first step: compute our walkpaths. It's from these that we will decide our candidates for contours
		walkpath = [rv]
		seen = set()
		seen.add(rv)
		reebstartvert = TVMap["valid-verts"][rv]
		#ignore any minimal paths
		if reebstartvert.iso < MinIso:
			continue
		while len(walkpath) != 0 and walkpath[-1] not in TVMap["reeb-end"]["vertset"]:
			# print(walkpath)
			topvert = TVMap["valid-verts"][walkpath[-1]]
			# print(topvert)
			#if we reach one of the ending triangle bands, break out of the loop, we have what we need
			is_end_of_walk = False
			if topvert.iso > (MaxIso - Epsilon):
				is_end_of_walk = True
			else:
				for t in topvert.trilist:
					if t in TVMap["reeb-end"]["triset"]:
						is_end_of_walk = True
						break
			if is_end_of_walk: break


			neighbors = topvert.neighbors_trilist.keys()
			proceed_walking = False
			for n in neighbors:
				if n in TVMap["reeb-start"]["vertset"] or n in seen:
					continue
				
				seen.add(n)
				neighbor_vert = TVMap["valid-verts"][n]
				if neighbor_vert.iso >= topvert.iso and neighbor_vert.iso <= (MaxIso):
					walkpath.append(n)
					proceed_walking = True
					break
			if proceed_walking:
				pass
			else:
				#we have reached a dead end, pop us off the walkpath
				walkpath.pop(-1)
		if len(walkpath) != 0:
			walklists.append(walkpath)
		# print(walkpath)
	# print(len(walklists))

	seen_contour_ids = set()
	#Todo: take our computed walk paths, and use them to determine which contours belong to what
	#	   for each walk, either it will be made invalid (because it trespassed on a taken contour), or it will contain a chain of contours in correct order
	for walk in walklists:
		newcontourlist = []
		partialSeen = set()
		for walkid in walk:
			walkvert = TVMap["valid-verts"][walkid]
			walktris = walkvert.trilist
			toProcess = True
			for t in walktris:
				for contour in ContourData:
					# pp.pprint(contour["id"])
					if t in contour["contour"]["tri_set"]:
						if contour["id"] in seen_contour_ids and contour["id"] not in contour_ignore_set:
							#we have trespassed on an existing walk, terminate ourselves
							toProcess = False
							print("Trespassed existing walk! Terminating...")
							if MinIso == 0.102527745:
								print("Caught Contour: " + str(contour["id"])+":"+str(contour["contour"]["centroid"]))
								for n in newcontourlist:
									print(str(n[3])+":"+str(n[4])+"\n")
							break
						else:
							# print(partialSeen)
							if contour["id"] not in partialSeen and contour["id"] not in contour_ignore_set:
								contourcentroid = contour["contour"]["centroid"]
								isovalue = contour["iso_level"]
								newcontourlist.append([contourcentroid[0], contourcentroid[1], contourcentroid[2], isovalue, contour["id"]])
								partialSeen.add(contour["id"])
				if not toProcess:
					break

			if not toProcess:
				break
		for i in list(partialSeen):
			seen_contour_ids.add(i)

		if not toProcess:
			continue
		#sort our new contourlist by the isovalue
		# pp.pprint(newcontourlist)
		newcontourlist.sort(key = lambda vec : vec[3])

		if MinIso == 0.102527745:
			for n in newcontourlist:

				print(str(n)+"\n")
		contourlistlist.append(newcontourlist)
	return contourlistlist


def GroupContours2(ContourData, Components, ReebStartVert, ReebEndVert):

	print("--- START GROUPING---")
	component_contour_set = dict()
	for c in Components:
		newset = {"id": c.id, "centroids":[], "contour-ids":[]}
		component_contour_set[c.id] = newset

	for con in ContourData:
		trilist = list(con["contour"]["tri_set"])
		#now determine which component we fit in
		comp_id = -1
		for comp in Components:
			for ti in trilist:
				if ti in comp.triset:
					comp_id = comp.id
					break
			if comp_id != -1: break

		if comp_id == -1: continue

		centroid_vector = con["contour"]["centroid"]
		isovalue = con["iso_level"]
		packed_vector = [centroid_vector[0],centroid_vector[1],centroid_vector[2], isovalue]
		component_contour_set[comp_id]["centroids"].append(packed_vector)
		component_contour_set[comp_id]["contour-ids"].append(con["id"])


	contourlistlist = []
	for k in component_contour_set.keys():
		newcontourlist = []
		for ci, c in enumerate(component_contour_set[k]["centroids"]):
			print("Adding Contour "+str(component_contour_set[k]["contour-ids"][ci])+" with centroid "+str(c)+" to arc of ("+str(ReebStartVert) + ","+str(ReebEndVert)+")")
			newcontourlist.append(c)
		newcontourlist.sort(key = lambda vec : vec[3])
		contourlistlist.append(newcontourlist)

	print("--- END GROUPING---")
	return contourlistlist

