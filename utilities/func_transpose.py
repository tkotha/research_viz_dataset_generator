import os
import os.path
import sys

def transposeFile(filename):
	columncount = 0
	rows = []
	with open(filename) as f:
		for line in f:
			parts = line.split(' ')
			columncount = len(parts)
			for i,p in enumerate(parts):
				if i == len(rows):
					rows.append([p])
				elif i < len(rows):
					rows[i].append(p)
				else:
					print("Error! there is a mismatch with the expected file structure!")
					return
	#now serialize this to a file
	with open("data_t_small.txt",'w') as f:
		s = ""
		for r in rows[0]:
			s+= str(r)+" "
		s = s[:-1]
		print(s,file=f)

	with open("data_t.txt",'w') as f:
		for i,rs in enumerate(rows):
			s = ""
			for r in rs:
				s+= str(r)+" "
			s = s[:-1]
			
			#if(i < 10000-1):
			#	s+="\n"
			print(s,file=f)
			print("finished row "+str(i))
		#s=s[:-1]
		#print(s,file=f)

	print("Done!")


if __name__ == "__main__":
	if len(sys.argv)  == 2:
		if os.path.isfile(sys.argv[1]):
			transposeFile(sys.argv[1])
		else:
			print("Error! path specified is not a file!")
	else:
		print("Error! please input only a file!")