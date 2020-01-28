import os
import sys
import os.path
import io
import ntpath
import json
import math
import numpy
from recordtype import recordtype
from collections import deque
from enum import Enum
from helper import *

meshvertcount = 0

class TraverseState(Enum):
	EDGELINK = 1
	TRIMAP = 2
#credit to http://code.activestate.com/recipes/576555/ for recordtype implementation
EdgeLinkData = recordtype('EdgeLinkData', 'contourvert contourvid explored tris')
TriData = recordtype('TriData', 'explored edges')
ContourData = recordtype('ContourData', 'contourvert, contourvid')
def map_iso(isovalue, minIso, maxIso, minPoint, maxPoint):
	mappoint = [map_float(isovalue, minIso, maxIso, minPoint[0], maxPoint[0]), \
			map_float(isovalue, minIso, maxIso, minPoint[1], maxPoint[1]), \
			map_float(isovalue, minIso, maxIso, minPoint[2], maxPoint[2])]
	return mappoint

def LoadEdgeLinkData(ContourVertList, ContourLineList, ContourTriList):
	edgelink = dict()
	for i in range(0, len(ContourTriList)):
		ti = ContourTriList[i]["tri"]
		e1, e2 = ContourTriList[i]["edges"]
		l1, l2 = ContourLineList[i]
		lv1, lv2 = ContourVertList[i]
		if e1["start"] not in edgelink:
			edgelink[e1["start"]] = dict()
		if e2["start"] not in edgelink:
			edgelink[e2["start"]] = dict()

		if e1["end"] not in edgelink[e1["start"]]:
			edata = EdgeLinkData(explored = False, tris = [], contourvert = lv1, contourvid = l1)
			edgelink[e1["start"]][e1["end"]] = edata
		if e2["end"] not in edgelink[e2["start"]]:
			edata = EdgeLinkData(explored = False, tris = [], contourvert = lv2, contourvid = l2)
			edgelink[e2["start"]][e2["end"]] = edata

		#append ti to our edge links
		edgelink[e1["start"]][e1["end"]].tris.append(ti)
		edgelink[e2["start"]][e2["end"]].tris.append(ti)

	return edgelink

def LoadTrimapData(ContourTriList):
	trimap = dict()
	for i in range(0, len(ContourTriList)):
		ti = ContourTriList[i]["tri"]
		e1,e2 = ContourTriList[i]["edges"]
		if ti not in trimap:
			tdata = TriData(explored = False, edges=[])
			trimap[ti] = tdata
		trimap[ti].edges.append(e1)
		trimap[ti].edges.append(e2)
	return trimap

#we're doing a basic mean, since the guys at TTK do something very similar (either mean coordinates or barycentric center, very similar)
def CalculateCentroid(ContourObject):
		# vertsize = Contour["vert_size"]
		# vertcount = Contour["vert_count"]
		vertsize = 3 #we basically assume three axes for x,y,z
		vertcount = len(ContourObject)
		avg = [0,0,0]
		for c in ContourObject:
			vi = c.contourvert
			avg[0] += vi[0]
			avg[1] += vi[1]
			avg[2] += vi[2]
			

		avg = [avg[0]/vertcount, avg[1]/vertcount, avg[2]/vertcount]
		return avg

#make sure that this is suitable for line object geometry
def PostProcessContour(ContourObject,VertCount):
	Contour = None
	contoursize = len(ContourObject)
	contour_vertlist = []
	contour_linelist = []
	contour_line_ordinal_list = []
	startvertcount = VertCount
	#build the vertex list
	for i in range(0,contoursize):
		vert = ContourObject[i].contourvert
		contour_vertlist.append(vert[0])
		contour_vertlist.append(vert[1])
		contour_vertlist.append(vert[2])
		startvertcount+=1

	#build the line indices list
	for i in range(0, contoursize):
		j = (i+1) % contoursize
		contour_linelist.append([i + VertCount, j + VertCount])
		contour_line_ordinal_list.append([i,j])

	Contour = {"vertices" : contour_vertlist, "line_indices": contour_linelist, "line_orderings" : contour_line_ordinal_list,"vertsize": 3, "vertcount": len(ContourObject)}
	return startvertcount,Contour

def ExploreEdgeLinkAndTriMap(edgelink, trimap, ContourVertList, ContourLineList, ContourTriList, StartingEdge):
		contour = []
		trilist = []
		Q = deque()
		TriQ = deque()
		traverse_mode = TraverseState.EDGELINK
		Q.append(StartingEdge)
		while len(Q) != 0 or len(TriQ) != 0:
			# print(Q)
			# print(TriQ)
			if traverse_mode == TraverseState.EDGELINK:
				current = Q.popleft()
				start = current["start"]
				end = current["end"]
				contour_data = ContourData(contourvert = edgelink[start][end].contourvert, contourvid = edgelink[start][end].contourvid)
				contour.append(contour_data)
				for t in edgelink[start][end].tris:
					if trimap[t].explored == False:
						TriQ.append(t)
						trimap[t].explored = True
						break
				edgelink[start][end].explored = True
				traverse_mode = TraverseState.TRIMAP

			elif traverse_mode == TraverseState.TRIMAP:
				t = TriQ.popleft()
				trilist.append(t)
				for e in trimap[t].edges:
					if edgelink[e["start"]][e["end"]].explored == False:
						Q.append(e)
						break
				traverse_mode = TraverseState.EDGELINK
		return (trilist, contour)

def TraverseEdgeLink(edgelink, trimap, ContourVertList, ContourLineList, ContourTriList, VertCount):
	contour_groups = []
	startvertcount = VertCount
	for i in range(0, len(ContourTriList)):
		ti = ContourTriList[i]["tri"]
		e1, e2 = ContourTriList[i]["edges"]
		if trimap[ti].explored == False:
			trilist, contour_object = ExploreEdgeLinkAndTriMap(edgelink, trimap, ContourVertList, ContourLineList, ContourTriList, e1)
			#perhaps some post processing is necessary here
			vertdelta, contourdata = PostProcessContour(contour_object, VertCount)
			startvertcount += vertdelta
			contour_groups.append({"contour_data":contourdata, "centroid":CalculateCentroid(contour_object), "tri_set":trilist})
		else:
			continue
	return startvertcount,contour_groups


# now we need to update our mesh data structure into something that is traversable
# ie, I now need to know how triangles are connected in order to properly decide how best to link contour lines
def CreateIsoLineData(UserIsos, VertexList, VertSize, TriList, FuncList):
	global meshvertcount
	def GetContours(ContourVertList, ContourLineList, ContourTriList, VertCount):
		tri_chains = []
		edgelink = LoadEdgeLinkData(ContourVertList, ContourLineList, ContourTriList)
		trimap = LoadTrimapData(ContourTriList)
		startvertcount, contour_groups = TraverseEdgeLink(edgelink, trimap, ContourVertList, ContourLineList, ContourTriList, VertCount)
		

		return startvertcount,contour_groups

	

	iso_vertlist = []
	iso_linelist = []
	vertcount = 0
	nudge_factor = .015

	contour_data = []
	meshvertcount = 0
	#this will be used to enable proper mesh traversal
	for iso in UserIsos:
		# print("Current Iso Level: " + str(iso))
		# print("StartVertCount: "+str(starting_vertcount))
		# create the line geometry instead as one contour set
		# rather than trying to link the contour lines by vertex positions (with the nightmare that is floating point)
		# perhaps try to keep a record of triangle ids traversed (so left tri, current tri, and right tri)
		# the question then is... how do we get left and right tris?
		contour_vertlist = []
		contour_linelist = []
		# this part will be crucial to getting connected components to work
		contour_trilist = []
		# contour_tri_chain = dict()
		#the tri_chain is a single element of three pieces that specify the current triangle, and the left and right triangle
		# we may not need it bc a) we will already have a triangle index list associated with each vertex/line element and 
		# b) using this trilist, we can perform floodfill search on the triangle neighbors map to figure out the right contour line groups
		for ti, tri in enumerate(TriList):

			#our first major roadblock... we have absolutely no idea who our neighbors are
			v1i = tri[0]
			v2i = tri[1]
			v3i = tri[2]

			i1 = FuncList[tri[0]]
			i2 = FuncList[tri[1]]
			i3 = FuncList[tri[2]]


			#now determine our two iso segment points 
			# xxx = v1, v2, v3, 0 = below, 1 = above
			iv1 = None
			iv2 = None
			#if we dont have iso anywhere near us, ignore this iteration
			# 000
			if i1 <= iso and i2 <= iso and i3 <= iso:
				continue
			# 111
			if i1 > iso and i2 > iso and i3 > iso:
				continue


			#therefore, ive changed vertex list to instead use an array of arrays for easier indexing
			v1 = VertexList[tri[0]]
			v2 = VertexList[tri[1]]
			v3 = VertexList[tri[2]]
			
			leftSide = []
			rightSide = []
			#we dont want the normal of the face, we want the normal of the lines
			#... come back to fixing the isoline thing, it's gonna take some math


			# assume counter clockise rotation
			# vert order:
			# 123


			# 3 cases for one point below the iso value
			# 011
			if i1 <= iso and i2 > iso and i3 > iso:
				iv1 = map_iso(iso, i1, i2, v1, v2)
				iv2 = map_iso(iso, i1, i3, v1, v3)
				# print("011")
				leftSide =  [v1i,v2i]
				rightSide = [v1i,v3i]
				
			# 101
			elif i1 > iso and i2 <= iso and i3 > iso:
				# print("101")
				iv1 = map_iso(iso, i2, i3, v2, v3)
				iv2 = map_iso(iso, i2, i1, v2, v1)
				leftSide =  [v2i,v3i]
				rightSide = [v2i,v1i]
			# 110
			elif i1 > iso and i2 > iso and i3 <= iso:
				
				# print("110")
				iv1 = map_iso(iso, i3, i2, v3, v2)
				iv2 = map_iso(iso, i3, i1, v3, v1)
				leftSide =  [v3i,v2i]
				rightSide = [v3i,v1i]

			# 3 cases for one point above the iso value
			# 100
			elif i1 > iso and i2 <= iso and i3 <= iso:
				# print("100")
				iv1 = map_iso(iso, i3, i1, v3, v1)
				iv2 = map_iso(iso, i2, i1, v2, v1)
				leftSide =  [v3i,v1i]
				rightSide = [v2i,v1i]
			# 010
			elif i1 <= iso and i2 > iso and i3 <= iso:
				# print("010")
				iv1 = map_iso(iso, i1, i2, v1, v2)
				iv2 = map_iso(iso, i3, i2, v3, v2)
				leftSide =  [v1i,v2i]
				rightSide = [v3i,v2i]
			# 001
			elif i1 <= iso and i2 <= iso and i3 > iso:
				# print("001")
				iv1 = map_iso(iso, i2, i3, v2, v3)
				iv2 = map_iso(iso, i1, i3, v1, v3)
				leftSide =  [v2i,v3i]
				rightSide = [v1i,v3i]
			assert iv1 is not None and iv2 is not None
			
			#prepare the single contour object here
			#now add them to the vert list and line list
			iv1_idx = vertcount#len(iso_vertlist)
			iv2_idx = iv1_idx+1
			
			contour_vertlist.append((iv1, iv2))	#we hold off actually creating the buffer geometry here, because we're not done sorting out the data
			vertcount += 2
			contour_linelist.append((iv1_idx,iv2_idx))
			#be sure to sort the ids of the leftside and right side
			leftSide = sorted(leftSide)
			leftEdge = {"start": leftSide[0], "end":leftSide[1]}
			rightSide = sorted(rightSide)
			rightEdge = {"start": rightSide[0], "end":rightSide[1]}
			#each entry of the tri list will have a)the current triangle, and b) the 2 edges expressed by vertices
			# i dont think we're fully concerned if this is slightly off, so long as the edges are unique, as we'll be doing flood fill regardless
			contour_trilist.append({"tri":ti, "edges": (leftEdge, rightEdge)})
			# contour_tri_chain[ti] = {"left": , "right":}

		#process the contour group blob to figure out the actual contour groups
		assert len(contour_trilist) == len(contour_vertlist) == len(contour_linelist)
		meshvertcount, contour_groups = GetContours(contour_vertlist, contour_linelist, contour_trilist, meshvertcount)

		#we will handle inputting the centroid in the contour objects themselves in GetContours
		for c in contour_groups:
			#add the contour object to the gigantic list here
			# print("finished contour_id: "+ str(len(contour_data)))
			contour_data.append({"id": len(contour_data), "contour":c, "iso_level":iso})

	# return (iso_vertlist, iso_linelist)
	return (contour_data, meshvertcount)

	

def ConvertContourDataToIsoLineRaw(Contours):
	iso_vertlist = []
	iso_linelist = []
	vertcount = 0
	nudge_factor = .015

	meshvertcount = 0
	selector = 0
	#try 25 and 14
	for contourdata in Contours:
		contour = contourdata["contour"]["contour_data"]
		meshvertsize = contour["vertcount"]
		startingaxis = 0
		for li in contour["line_orderings"]:
			li1 = li[0]
			li2 = li[1]
			iso_linelist.append([li1 + meshvertcount, li2 + meshvertcount])
		for vert in contour["vertices"]:
			iso_vertlist.append(vert)
			startingaxis += 1
			if startingaxis >= 3:
				startingaxis = 0
				meshvertcount += 1
	return (iso_vertlist, iso_linelist, meshvertcount)

#bring back the raw version of drawing the isoline data
def CreateIsoLineDataRaw(UserIsos, VertexList, VertSize, TriList, FuncList):
	iso_vertlist = []
	iso_linelist = []
	vertcount = 0
	nudge_factor = .015

	meshvertcount = 0

	for iso in UserIsos:
		for ti, tri in enumerate(TriList):
			#our first major roadblock... we have absolutely no idea who our neighbors are
			v1i = tri[0]
			v2i = tri[1]
			v3i = tri[2]

			i1 = FuncList[tri[0]]
			i2 = FuncList[tri[1]]
			i3 = FuncList[tri[2]]


			#now determine our two iso segment points 
			# xxx = v1, v2, v3, 0 = below, 1 = above
			iv1 = None
			iv2 = None
			#if we dont have iso anywhere near us, ignore this iteration
			# 000
			if i1 <= iso and i2 <= iso and i3 <= iso:
				continue
			# 111
			if i1 > iso and i2 > iso and i3 > iso:
				continue


			#therefore, ive changed vertex list to instead use an array of arrays for easier indexing
			v1 = VertexList[tri[0]]
			v2 = VertexList[tri[1]]
			v3 = VertexList[tri[2]]
			
			leftSide = []
			rightSide = []
			#we dont want the normal of the face, we want the normal of the lines
			#... come back to fixing the isoline thing, it's gonna take some math


			# assume counter clockise rotation
			# vert order:
			# 123


			# 3 cases for one point below the iso value
			# 011
			if i1 <= iso and i2 > iso and i3 > iso:
				iv1 = map_iso(iso, i1, i2, v1, v2)
				iv2 = map_iso(iso, i1, i3, v1, v3)
				# print("011")
				leftSide =  [v1i,v2i]
				rightSide = [v1i,v3i]
				
			# 101
			elif i1 > iso and i2 <= iso and i3 > iso:
				# print("101")
				iv1 = map_iso(iso, i2, i3, v2, v3)
				iv2 = map_iso(iso, i2, i1, v2, v1)
				leftSide =  [v2i,v3i]
				rightSide = [v2i,v1i]
			# 110
			elif i1 > iso and i2 > iso and i3 <= iso:
				
				# print("110")
				iv1 = map_iso(iso, i3, i2, v3, v2)
				iv2 = map_iso(iso, i3, i1, v3, v1)
				leftSide =  [v3i,v2i]
				rightSide = [v3i,v1i]

			# 3 cases for one point above the iso value
			# 100
			elif i1 > iso and i2 <= iso and i3 <= iso:
				# print("100")
				iv1 = map_iso(iso, i3, i1, v3, v1)
				iv2 = map_iso(iso, i2, i1, v2, v1)
				leftSide =  [v3i,v1i]
				rightSide = [v2i,v1i]
			# 010
			elif i1 <= iso and i2 > iso and i3 <= iso:
				# print("010")
				iv1 = map_iso(iso, i1, i2, v1, v2)
				iv2 = map_iso(iso, i3, i2, v3, v2)
				leftSide =  [v1i,v2i]
				rightSide = [v3i,v2i]
			# 001
			elif i1 <= iso and i2 <= iso and i3 > iso:
				# print("001")
				iv1 = map_iso(iso, i2, i3, v2, v3)
				iv2 = map_iso(iso, i1, i3, v1, v3)
				leftSide =  [v2i,v3i]
				rightSide = [v1i,v3i]
			assert iv1 is not None and iv2 is not None
			
			#prepare the single contour object here
			#now add them to the vert list and line list
			iv1_idx = vertcount#len(iso_vertlist)
			iv2_idx = iv1_idx+1
			
			iso_vertlist.append(iv1[0])
			iso_vertlist.append(iv1[1])
			iso_vertlist.append(iv1[2])
			iso_vertlist.append(iv2[0])
			iso_vertlist.append(iv2[1])
			iso_vertlist.append(iv2[2])
			# contour_vertlist.append((iv1, iv2))	#we hold off actually creating the buffer geometry here, because we're not done sorting out the data
			vertcount += 2
			iso_linelist.append([iv1_idx,iv2_idx])
	return (iso_vertlist, iso_linelist, vertcount)