notes for the dataset generator

..ok, it looks like in order to actually have recon combine my mesh with my func data... I may have to actually go ahead and export both of them into something like a combined off file. otherwise this gets annoying fast. One thing I should ask rosen is a) for the current paper, can I assume a 3d model, and b)for the reeb graph program, can it read one function at a time (this allows me to statically set the index to say 4). If I try to force this to work for an obj and func file... this means rewriting a good chunk of the internals... but if instead I can convert the obj and func pair into an off model (the same applies for conn-geo as well), then that would play much more nicely with recon

...actually, i should probably just augment the obj file to also include its own func index, it'd be simple to do, and can be done from a python conversion script. I'd need a .objf file to distinguish it tho For this reason, the OBJ_FUNC custom loader is likely needed

since we are dealing with opening and writing falls a lot, it is probably better to be sure we are streaming file handles rather than actually loading files into memory

change of plans, args will not be split by :, instead by |, to reduce likeliness of conflict

FUNCTIONS NEEDED : 

		###ReebFileToGraphViz --probably not needed


		[x]parseArgFile
		[x]parseBargFile
		[x]getCommonSubstring
		[x]PDPairFileToCSV
		[x]ReebFileToPDPair --need to make sure windows paths work correctly before proceeding. this may also require revision depending on what we do with project setup
		[x] ProcessEmptyFunc --just generates a 0 valued func list
		[x] CreateOBJF(funcfile, objfile, dest_objf_file)
		[x] ExtractFuncFromOBJF(objf_file, dest_func_file, dest_obj_file)


note: the v1 simply means we anticipate this being feature complete, but may encounter either new feature requests or bugs to fix
TODO: [DONE - v1]

[x] modify existing model helper functions so that conversion methods return the file/path name of the file that was generated

[x] re-establish the main command line script for handling the input experiment folder. The inputs should be the model, the function files or function specifications, as ordered in the respective arg file (we always interface with the arg file)
[x] make sure that obj and conn/geo models are both properly handled (conversion where needed, likely from conn-geo to obj), and that function files are generated

[x] once model and function files are verified to be produced correctly, proceed to wire the recon code. It will need the ability to import arbitrary obj models and the corresponding function files via the command line (rather than its properties text file). Use an external build/jar path for the recon code so that it can be reconfigured as needed
	x enable recon to handle model and func files from command line arguments
	x make sure python can successfully call recon with a sample batch
	x update recon to be able to import models and function files as needed
	x ensure that the final result produces a proper reeb graph in the correct directory
note: we do not import obj and func files directly anymore, rather we now export to an intermediary objf file to streamline the process. the loading process works identically to obj otherwise

[x] after the reeb graph is generated, make sure that cp_pairs can also be generated