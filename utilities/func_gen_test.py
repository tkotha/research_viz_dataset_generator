aprime = [.1,.2,.3]
snr    = [ 1, 2, 3]
numOfF = [ 2, 3, 4]

final_list = []
for a in aprime:
	combolist = []
	for s in snr:
		combolist2 = []
		for n in numOfF:
			combolist2.append({"# of features": n})
		combolist.append(["SNR : " + str(s), "ENTRIES" , combolist2])
	final_list.append({"APRIME" : a, "ENTRIES" : combolist})


import pprint

pp = pprint.PrettyPrinter(indent = 4)
pp.pprint(final_list)
