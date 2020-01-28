import os
import sys
import os.path
import ntpath
#-------------------------RECON RELATED HELPER FUNCTIONS-------------------
# no, I am not ashamed at all
reeb_recon_path = "..\\external\\recon\\computeReebGraph.bat"

pair_jar_path = "..\\external\\ReebGraphPairing\\ReebGraphPairing.jar"
# def createReebFile(modelFilePath, funcFilePath):
# 	os.system(reeb_recon_path +" "+ modelFilePath +" "+funcFilePath)

def createReebFile(OBJFPath, ReebFilename):
	os.system(reeb_recon_path +" "+OBJFPath+" "+ReebFilename)

#------------------------REEB GRAPH CONVERSION RELATED HELPER FUNCTIONS--------
# here we have the reeb file to graphviz function i guess?
# note: judging from recent discussions with rosen, this step may be unnecessary, 
# as we'll use the existing visualization code to embed the reeb graph in 3d instead


# here we have the reeb file to pd pair file
def ReebFileToPDPair(ReebGraphPath):
	#handle the really odd case regarding windows paths not handling \\ correctly
	pdpairpath = ReebGraphPath.replace("\\","/")
	os.system(pair_jar_path+" "+pdpairpath)
	reebname = ntpath.basename(ReebGraphPath)
	reebfilename = os.path.splitext(reebname)[0]
	reebext = os.path.splitext(reebname)[1]
	reebpath = os.path.dirname(os.path.abspath(ReebGraphPath))
	return (os.path.join(reebpath, "pd0_"+reebname), os.path.join(reebpath, "pd1_"+reebname))

#for now, returns a tuple of sets of vertices and edges
# the verts are a mix of [id, fvalue], and the edges are [vert1, vert2]
def OpenReebGraph(ReebGraphPath):
	reeb_graph_data = [[], []]
	with open(ReebGraphPath, 'r') as reeb:
		for line in reeb:
			if line.startswith('v'):
				#load vertex
				parts = line.split()
				reeb_graph_data[0].append([int(parts[1]), float(parts[2])])
			elif line.startswith('e'):
				#load edge
				parts = line.split()
				reeb_graph_data[1].append([int(parts[1]), int(parts[2])])
	return reeb_graph_data
