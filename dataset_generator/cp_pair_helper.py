import os
import os.path
import sys
import random
import numpy
import math
import csv


#-----------------PD_PAIR FILE RELATED HELPER FUNCTIONS---------------------
# example line: 3499/2695 [4.698147,5.684675)
def parsePairLine(line,num):
	pdl = line.split()
	assert len(pdl) == 2
	#dissect the second line
	pdl[1] = pdl[1][:-1]
	pdl[1] = pdl[1][1:]
	return pdl[1]+","+str(num)

#note: implicitly saves to PDFile Location
#so parsing the pd file is going to be a bit verbose, so do not expect this to be portable code
def PDPairFileToCSV(PDFilePath):
	CSVPath = os.path.splitext(PDFilePath)[0] + ".csv"
	with open(PDFilePath, 'r') as pd, open(CSVPath,'w') as csv:
		csvstring ="x,y,type\n" 
		for line in pd:
			csvstring += parsePairLine(line,0)+"\n"
		csvstring = csvstring[:-1]
		csv.write(csvstring)

def PDPairFileToCSV(PD0FilePath, PD1FilePath,CSVPath):
	with open(PD0FilePath, 'r') as pd0, open(PD1FilePath,'r') as pd1, open(CSVPath, "w") as csv:
		csvstring = "x,y,type\n"
		for line in pd0:
			csvstring += parsePairLine(line,0)+"\n"
		for line in pd1:
			csvstring += parsePairLine(line,1)+"\n"
		csvstring = csvstring[:-1]
		csv.write(csvstring)

def ImportCSVFile(CSVPath):
	pd_pair_data = []
	with open(CSVPath,'r') as csvfile:
		csvreader = csv.DictReader(csvfile)
		for row in csvreader:
			pd_pair_data.append([float(row['x']), float(row['y']), row['type']])
	print(pd_pair_data)
	return pd_pair_data

