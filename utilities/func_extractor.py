import os
import os.path
import sys

# this is a one off script to deal with combined function files
# ideally we want each function file to be isolating its own particular function
# this way, it is much easier for the other programs to handle the data

#note, this script MUST be run in the same directory as the file in question!

def createAugmentedFileName(filename, id):
	return os.path.splitext(filename)[0]+"_"+str(id)+".txt"

#arguments required: function file
if __name__ == "__main__":
	assert len(sys.argv) == 2
	line_id = 0
	with open(sys.argv[1], 'r') as big_file:
		for line in big_file:
			newfile = createAugmentedFileName(big_file.name, line_id)
			print(newfile)
			with open(newfile, 'w') as nf:
				nf.write(line)
			line_id += 1
		