import pprint
APrimes = [.1,.2,.3,.4,.5]

A0Primes = [.0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.0,1.1,1.2,1.3,1.4]
A1Primes = [.0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.0,1.1,1.2,1.3,1.4]
SNRs =     [.5,.6,.7,.8,.9,1.0]
NOFs =     [2,3,4,5,6,7,8,9,10,11]

#goal, produce scheme to generate all possible combinations
#first, pair up all possible distances
for ap in APrimes:
	a01Pairs = []
	finalResults = []
	seenPairs = set()
	for a0 in A0Primes:
		for a1 in A1Primes:
			if abs(a0 - a1) >= ap - .0001 and abs(a0 - a1) <= ap + .0001:
				pair = tuple(sorted([a0,a1]))
				if pair not in seenPairs:
					seenPairs.add(pair)
					a01Pairs.append((a0,a1))
	for pair in a01Pairs:
		for snr in SNRs:
			for nof in NOFs:
				finalResults.append((pair[0],pair[1],snr,nof))
	pp = pprint.PrettyPrinter(indent = 2)
	print("For Aprime " +str(ap)+": ")
	# pp.pprint(finalResults)
	print(len(finalResults))