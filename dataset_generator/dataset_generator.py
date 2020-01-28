import sys
import os
import glob
import os.path
import ntpath
import math
from helper import *
from model_helper import *
from func_helper import *
from reeb_helper import *
from cp_pair_helper import *
from argfile_helper import *
from batchfile_helper import *
from shutil import copyfile
# for the recon code, this is the command to run, along with arguments:
# java -Xmx3g -classpath path/to/recon.jar vgl.iisc.cmd.ReCon arg1 arg2 etc..

cmdargs = {"arg-file":"",
		   "obj-file":"",
		   "path":os.getcwd()}
PairingDelimiter = "::"

def resetCmdArgs():
	cmdargs = {"arg-file":"",
		   "path":os.getcwd()}

def parseCmdArgs(args):
	for i in range(0,len(args)):
		s = args[i]
		if s == "":
			continue
		parts = s.split(PairingDelimiter)
		if len(parts) != 2:
			print("error, invalid arg "+s+"\n")
			print("make sure you are using the form key::value for each argument")
			exit()
		parts[0].strip()
		parts[1].strip()
		if parts[0] not in cmdargs:
			print("error, unrecognized argument " + parts[0])
		else:
			if parts[0] == "path":
				#process path
				if os.path.isabs(parts[1]):
					cmdargs[parts[0]] = parts[1]
				else:
					cmdargs[parts[0]] = os.path.join(cmdargs[parts[0]], parts[1])
					if not os.path.exists(cmdargs[parts[0]]):
						print("error, the specified path \""+parts[1]+"\" does not exist! Abort experiment!")
						exit()
			else:
				cmdargs[parts[0]] = parts[1]


def handleBargsFile(path, bargfile, verbose = False):
	#check for bargfile validity
	files = getFiles(path, "bargs")
	target_bargfile = argFileValidity(files, bargfile)

	#now to parse the barg file
	fileargs = parseBargFile(target_bargfile, path)
	if verbose:
		print(json.dumps(fileargs, indent=4))
	#check for any errors, and print them out
	if fileargs["validation-error"]:
		print(fileargs["error-reason"])
		exit()
	print("-----BEGIN BATCHING-----")
	#now with the fileargs in hand, execute it
	for i,b in enumerate(fileargs["batches"]):
		if os.path.isabs(b["path"]):
			handleArgsFile(b["path"], b["arg-file"])
		else:
			handleArgsFile(os.path.join(fileargs["path"],b["path"]), b["arg-file"])
		print("--- done handling "+b["path"]+" ---")

def handleArgsFile(path, argfile, verbose = True):
	#check for argfile validity
	files = getFiles(path, "args")
	target_argfile = argFileValidity(files, argfile)

	#now to parse the arg file
	fileargs = parseArgFile(target_argfile, path)
	fileargs["path"] = path
	#check for any errors, and print them out
	if fileargs["validation-error"]:
		print(fileargs["error-reason"])
		exit()

	#now with fileargs in hand, execute it
	if verbose:
		print(json.dumps(fileargs, indent=4))
	
	#first, check the model, if using obj, or if using conn geo
	usingObj = fileargs["model"]["obj"] is not "" 
	usingHighRes = fileargs["high-res-model"]["obj"] is not ""
	#if not using obj, force the conversion so we operate in obj
	if not usingObj:
		assert fileargs["model"]["conn"] is not "" and fileargs["model"]["geo"] is not ""
		#set the model obj to use the filename common to conn and geo
		#now we need to run the helper function to convert to an obj model
		fileargs["model"]["obj"] = os.path.splitext(fileargs["model"]["conn"])[0]+"_"+os.path.splitext(fileargs["model"]["geo"])[0]+"_toObj.obj"
		connpath = os.path.join(path, fileargs["model"]["conn"])
		geopath = os.path.join(path, fileargs["model"]["geo"])
		objpath = os.path.join(path, fileargs["model"]["obj"])
		convertConnGeoToOBJ(connpath, geopath, objpath)
		usingObj = fileargs["model"]["obj"] is not ""
	
	highresCheckPath = determineAbsOrRelativePath(fileargs["high-res-model"]["obj"], path)
	assert usingHighRes and os.path.isfile(highresCheckPath)

	objcheckpath = determineAbsOrRelativePath(fileargs["model"]["obj"], path)
	assert usingObj and os.path.isfile(objcheckpath)
	
	#now we need to open the obj model to access its vertex data
	objModel = OpenObj(objcheckpath)
	highResObjModel = OpenObj(highresCheckPath)
	highresvertmap = CreateVertMap(len(highResObjModel[0]), highResObjModel[1], highResObjModel[0])

	modelname = fileargs["model"]["obj"].split('.')[0]
	
	#now we go through the function generation stuff (we don't need to inspect any function files)
	#if any function gen requires a func file as a parameter, we need to make sure it actually exists in the func file list
	#this portion of code needs to be adjusted to handle multiple functions at once most likely
	if fileargs["generate-reeb-list-if-not-specified"] and len(fileargs["reeb-list"]) != 0:
		fileargs["generate-reeb-list-if-not-specified"] = False

	#use an organizer structure to pair up functions and reeb files
	#so instead of iterating over reeb files manually, we iterate over the organizer, and use that to prepare the json files
	organizer = []
	'''
	organizer structure
		list of experiments
		experiment is a list of func,reeb pairings for each result of func_result
	'''

	for i,func in enumerate(fileargs["func-list"]):
		#if we have more specific cases, like invocation specific arguments, we'd also check that here
		#now we check for the filename, if it doesnt exist, we generate one
		#for each time a function is generated, we need to make sure to 
		#a)generate the file, and b)make sure it's added to the func file list
		function = func[0]
		func_args = func[2]
		func_organizer = []
		repeatCount = 1
		if "repeat" in func_args:
			repeatCount = func_args["repeat"]
		for repi in range(0, repeatCount):
			#make sure to feed in the arguments and the vertices of the model
			func_result = func_table[function](objModel[0], highresvertmap, func_args)
			# print(func_result)
			funcname = func[1]
			# if  funcname is "":
			func_experiment_organizer = [funcname]
			for fri, fr in enumerate(func_result):
				#now we want to export our func_result as each instance (note func result may return more than 1 function)
				funcname = function+"_"+str(i+1)+"_"+str(repi)+"_"+str(fri)+".txt"
				# elif not funcname.endswith(".txt"):
					# funcname += ".txt"
				print(funcname)
				fileargs["func-files"].append(funcname)
				#append the reeb file pairing here
				if fileargs["generate-reeb-list-if-not-specified"]:
					ri = len(fileargs["reeb-list"])+1
					reebname = modelname + "_reeb"+str(ri)+".txt"
					fileargs["reeb-list"].append([reebname, funcname])
					func_experiment_organizer.append([reebname, funcname, func_args])

				#now write the funcfile... do we need to include the path too?
				#rather... should we be setting the current working directory with respect to the argfile first?
				funcpath = determineAbsOrRelativePath(funcname, path) #os.path.join(path, funcname) #or just funcname?
				#here we enforce the constraint that each file must contain only 1 function
				WriteSingleFunc(funcpath, fr)
			func_organizer.append(func_experiment_organizer)
		organizer.append(func_organizer)

	print(organizer)
	# go ahead and convert obj to json file. we wont need it, but the webcode might
	modeljsonpath = os.path.splitext(objcheckpath)[0] + "_model.json"
	convertOBJModelToJSON(objModel, modeljsonpath)

	#once all the funcs have been generated, and we are sure that the func file list is now good to go
	#it is time to go through the reeb list, and execute the following in order for each item:
	'''
		
		convertFuncAndOBJToOBJF(testfolder + "geometry_connectivity_toObj.obj", testfolder + "data_t_small.txt")
		createReebFile(testmodel+"f")
		ReebFileToPDPair(testfolder+"geometry_connectivity_toObj_export.rg")
		PDPairFileToCSV(testfolder +"pd0_geometry_connectivity_toObj_export.rg")
	'''
	#with this, the only thing we really need to change is how the json files are configured. What we need here are 2 functions side by side for comparison
	#so the jsons need to reflect that
	#we use the original convertFuncAndOBJtoJSON function to produce 2 datasets, using different functions as the input, and then package those things together into files that we export
	#this means we need to modify that function to not handle the file writing, but instead do that here
	#we need a way to map all generated reeb graphs to all possible functions (now we expect each function spec to do more than 1 function) automatically

	#note that now we have done this, we cannot go back to the "old" way of processing data
	#now we must push ahead to make sure a)the functions are implemented and return 2 functions at a time, b)that we get "side by side" json data, and c)each json experiment file loads correctly in the web code, one file, 2 visualizations

	# for reeb in fileargs["reeb-list"]:

	for func in organizer:
		for trial_i, trial in enumerate(func):
			print(trial)
			print(trial[1])
			trialName = trial[0]
			print("Trial Name: " + trialName)
			#the point of iterating through ALL the experiments like this in a single trial, is to make sure we have the ablity to group them into jsons as needed
			#only process the datasets inside this inner loop
			datasets = []
			combined_pd_json = []
			metadata = None
			for parti, part in enumerate(trial):
				if parti == 0: continue
				#if paths need to be constructed, do it here
				#note: need to modify current reeb helper functions to allow exporting to a new name
				reeb_filename = part[0]
				func_filename = part[1]
				print("Func File Name: " +func_filename)
				contour_grouping_epsilon_value = .01
				grouping_strategy = 1
				for fn in fileargs["func-list"]:
					if fn[1] == trialName:
						print("Found function!")
						if "contour_grouping_epsilon" in fn[2].keys():
							print("set epsilon")
							contour_grouping_epsilon_value = fn[2]["contour_grouping_epsilon"]
						if "grouping_strategy" in fn[2].keys():
							print("set grouping strategy")
							grouping_strategy = fn[2]["grouping_strategy"]
						break
				func_filename = determineAbsOrRelativePath(func_filename,path)
				objfpath = convertFuncAndOBJToOBJF(objcheckpath, func_filename)
				
				# print(objfpath)
				reeb_path = determineAbsOrRelativePath(reeb_filename, path)
				createReebFile(objfpath, reeb_path)
				pd_path = ReebFileToPDPair(reeb_path)
				csvpath = os.path.join(path, "pd_"+os.path.splitext(ntpath.basename(reeb_path))[0]+".csv")
				PDPairFileToCSV(pd_path[0], pd_path[1], csvpath)
				combined_pd_json.append(ImportCSVFile(csvpath))
				#this will be key to enabling us to group multiple datasets together into single experiment files
				dataset = convertFuncAndOBJToJSON_WithIsoAndReeb(objcheckpath, func_filename, reeb_path, csvpath, contour_grouping_epsilon_value, grouping_strategy)
				datasets.append(dataset)
				if metadata is None:
					functionName = trialName
					if '.' in functionName:
						functionName = (os.path.splitext(functionName)[0]).split('_')[0]
					metadata = {"metadata" : part[2], "function-name" : functionName, "model-name" : modelname}
				
			isopath = datasets[0]["isolines"][1]
			reebpath = datasets[0]["reeb"][1]
			funcpath = datasets[0]["funcs"][1]
			pdpath = funcpath.replace("_func","_pd")
			
			combined_reeb_json = []
			combined_iso_json = []
			combined_func_json = []
			for d in datasets:
				combined_reeb_json.append(d["reeb"][0])
				combined_iso_json.append(d["isolines"][0])
				combined_func_json.append(d["funcs"][0])

			combined_reeb_json.append(metadata)
			combined_iso_json.append(metadata)
			combined_func_json.append(metadata)
			combined_pd_json.append(metadata)
			assert len(combined_reeb_json) == 3
			assert len(combined_pd_json) == 3
			assert len(combined_iso_json) == 3
			assert len(combined_func_json) == 3

			with open(isopath, 'w') as isojson, open(reebpath, 'w') as reebjson, open(funcpath, 'w') as funcjson, open(pdpath,'w') as pdjson:
				# reeb_json = datasets[0]["reeb"][0]
				# iso_json =  datasets[0]["isolines"][0]
				# func_json = datasets[0]["funcs"][0]
				json.dump(combined_reeb_json, reebjson, indent = 4)
				json.dump(combined_iso_json, isojson, indent = 4)
				json.dump(combined_func_json, funcjson, indent = 4)
				json.dump(combined_pd_json, pdjson, indent = 4)
			reebjson_min = minify(datasets[0]["reeb"][1])
			isojson_min = minify( datasets[0]["isolines"][1])
			funcjson_min = minify(datasets[0]["funcs"][1])
			pdjson_min = minify(pdpath)

			#make sure to copy the files to our desired location if it exists
			copyPath = fileargs["copy-folder"]
			enable_sub_folder = True
			function_folder = metadata["function-name"]
			category_folder = "APrimeDist"
			os.makedirs(copyPath, exist_ok=True)

			if trial_i == 0:
				copyfile(modeljsonpath+".zip", os.path.join(copyPath, getFileNameText(modeljsonpath) +".zip"))

			reeb_file_ext = getFileNameText(reebjson_min).split('_')[-1]
			iso_file_ext = getFileNameText(isojson_min).split('_')[-1]
			func_file_ext = getFileNameText(funcjson_min).split('_')[-1]
			pd_file_ext = getFileNameText(pdjson_min).split('_')[-1]

			if copyPath != "":
				copyreeb = ""
				copyiso = ""
				copyfunc = ""
				copypd = ""

				if enable_sub_folder:
					print(metadata)
					nof = str(metadata["metadata"]["numOfFeatures"])
					snr = str(int(metadata["metadata"]["desiredSNR"]))
					stub = "snr_"+snr+"_nof_"+nof+"_"+metadata["model-name"]+"_"+metadata["function-name"]+"_"


					copysubpath1 = os.path.join(copyPath, function_folder)
					if not os.path.exists(copysubpath1):
						os.mkdir(copysubpath1)
					copysubpath2 = os.path.join(copysubpath1, category_folder + "_"+str(metadata["metadata"][category_folder]).replace(".","dot"))
					if not os.path.exists(copysubpath2):
						os.mkdir(copysubpath2)

					copyreeb =	os.path.join(copysubpath2, stub+reeb_file_ext)
					copyiso = 	os.path.join(copysubpath2, stub+iso_file_ext)
					copyfunc = 	os.path.join(copysubpath2, stub+func_file_ext)
					copypd = 	os.path.join(copysubpath2, stub+pd_file_ext)
				else:
					copyreeb = os.path.join(copyPath, stub+getFileNameText(reebjson_min))
					copyiso = os.path.join(copyPath,  stub+getFileNameText(isojson_min))
					copyfunc = os.path.join(copyPath, stub+getFileNameText(funcjson_min))
					copypd = os.path.join(copyPath,   stub+getFileNameText(pdjson_min))


				copyfile(reebjson_min, copyreeb)
				copyfile(isojson_min, copyiso)
				copyfile(funcjson_min, copyfunc)
				copyfile(pdjson_min, copypd)




	# after this, do any final touchup work that needs to be done, quick conversions, extension corrections, etc.

	#at this point, we should be done with the argfile, conserve space by deleting all tmp files
	DeleteUnnecessaryFiles(os.path.join(path, "*_compressed.json.gz"))
	DeleteUnnecessaryFiles(os.path.join(path, "*.objf"))
	DeleteUnnecessaryFiles(os.path.join(path, "*_minify.json"))
	DeleteUnnecessaryFiles(os.path.join(path, "*_msgpack.json"))
	DeleteUnnecessaryFiles(os.path.join(path, "*_bin.json"))
	DeleteUnnecessaryFiles(os.path.join(path, "*.txt"))
	DeleteUnnecessaryFiles(os.path.join(path, "*.json"))
	DeleteUnnecessaryFiles(os.path.join(path, "*.rg"))
	pass


def DeleteUnnecessaryFiles(filepathPattern):
	fileList = glob.glob(filepathPattern)
	for filepath in fileList:
		try:
			os.remove(filepath)
		except:
			print("Error while deleting file: " + filepath)
#to edit the recon path, go to the reeb_helper file!
# testmodel = "C:\\work\\research\\project\\dataset_generator\\test\\rosen_flat_mesh\\geometry_connectivity_toObj.obj"
# testfolder = "C:\\work\\research\\project\\dataset_generator\\test\\rosen_flat_mesh\\"
if __name__ == "__main__":
	parseCmdArgs(sys.argv[1:])
	isBatch = False

	if cmdargs["obj-file"] is not "":
		#convert to conngeo
		checkpath = determineAbsOrRelativePath(cmdargs["obj-file"], cmdargs["path"])
		convertOBJtoConnGeo(checkpath, os.path.splitext(checkpath)[0]+"_conn.txt", os.path.splitext(checkpath)[0]+"_geo.txt")
	else:
		if cmdargs["arg-file"].endswith(".bargs"):
			isBatch = True
		elif not cmdargs["arg-file"].endswith(".args"):
			print("ERROR: You must supply either a .bargs or .args file! QUITTING")
			exit()
		if isBatch:
			print("handling batch...")
			handleBargsFile(cmdargs["path"], cmdargs["arg-file"])
		else:
			print("handling one experiment...")
			handleArgsFile(cmdargs["path"], cmdargs["arg-file"])


'''
proper example usage:
always make sure to specify the path folder properly first, without a trailing \\ or /
that is the path argument
then the arg-file argument is JUST THE NAME of the target file! do not append a path in that

example
python dataset_generator.py path:..\\data\\test arg-file:rosen_flat_meshes.bargs


'''