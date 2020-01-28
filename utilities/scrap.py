def GatherReebEdgeCentroids(reebverts, reebedges, funclist, trilist, tvmap, contourdata):
	reeb_edge_arcs = []
	contourlist = InitContours(contourdata)

	for edge in reebedges:
		start = None
		end = None

		for v in reebverts:
			if v[0] == edge[0]:
				start = ReebEndData(id = v[0], iso = v[1], triset = set())
			elif v[0] == edge[1]:
				end = ReebEndData(id = v[0], iso = v[1], triset = set())
		assert end is not None and start is not None
		#now collect triangles for start and end
		for r in [start,end]:
			#first collect all connected tris
			for v in tvmap[r.id].neighbors_trilist.keys():
				for t in tvmap[r.id].neighbors_trilist[v]:
					r.triset.add(t)

			#now perform an iso contour check in case of saddles
			for t in tvmap[r.id].trilist:
				tri = trilist[t]
				v1i = tri[0]
				v2i = tri[1]
				v3i = tri[2]

				i1 = funclist[v1i]
				i2 = funclist[v2i]
				i3 = funclist[v3i]

				#eliminate outside cases
				if i1 <= r.iso and i2 <= r.iso and i3 <= r.iso: continue
				if i1 > r.iso and i2 > r.iso and i3 > r.iso: continue
				#for the remaining 6 cases, we just care if the tri is in the contour line at all
				#so we should be able to add it directly at this point
				r.triset.add(t)

		reebwalkers = ReebWalkers(walkers = [], done = False, winner = -1)

		#now take the starting point of the reeb walk, and set up the walkers
		for vn in tvmap[start.id].neighbors_trilist.keys():
			if tvmap[vn].iso > start.iso:
				#create new reeb walker
				new_walker = ReebWalkerData(current_vert = vn, current_iso = funclist[vn], contour_id_list = [], history = [], done = False)
				#scan through contour list to collect initial contours
				for ci,contour in enumerate(contourlist):
					if contour.contour_iso < start.iso: 
						continue
					elif contour.contour_iso >= start.iso and contour.contour_iso <= tvmap[vn].iso and contour.taken == False:
						for t in tvmap[start.id].neighbors_trilist[vn]:
							if t in contour.triset:
								print("adding contour!!!")
								assert False #we didnt even hit this assert once... thats pretty bad
								#now we can add it and exit the loop, worst case, nothing happens
								new_walker.contour_id_list.append(contour.contour_id)
								break
					elif contour.contour_iso > tvmap[vn].iso:
						break
				reebwalkers.walkers.append(new_walker)

		#do a final prelim check to see if any of our newly made reeb walkers is already at the end point
		#because we made sure to collect contours before hand, we should just be able to quit without any side effects
		for walker in reebwalkers.walkers:
			if walker.current_vert == end.id:
				reebwalkers.done = True
				reebwalkers.winner = True
				break

		#now the reeb walkers should be setup
		walkers_stalled = False
		while not reebwalkers.done and not walkers_stalled:
			for wi, walker in enumerate(reebwalkers.walkers):
				#check if our best edge's tris touch any contours
				if walker.done: continue
				nextid = tvmap[walker.current_vert].max_vid
				if nextid == walker.current_vert:
					walker.done = True
					continue
				newtrilist = []
				for key in tvmap[walker.current_vert].neighbors_trilist.keys():
					if key == nextid:
						for ti in tvmap[walker.current_vert].neighbors_trilist[key]:
							newtrilist.append(ti)
						break
				# assert newtrilist is not None ##because of how the reeb walkers are setup to allow potential duplicate branches, we may not be able to gaurantee this
				for tri in newtrilist:
					for c in contourlist:
						if tri in c.triset and c.contour_id not in set(walker.contour_id_list) and not c.taken:
							walker.contourlist.append(c.contour_id)
				#now check to see if we've touched the end
				#because weve already collected contours, we should be good to go
				#we should only need to see that max_vid is the end point, our walker itself should never be the end point
				for tri in newtrilist:
					if tri in end.triset or tvmap[walker.current_vert].max_vid == end.id:
						reebwalkers.done = True
						reebwalkers.winner = wi
						#assuming all contours were collected in the previous step this should be it
						break
				if reebwalkers.done: break
				#update our walker with the next point
				walker.history.append(walker.current_vert)
				walker.current_iso = tvmap[walker.current_vert].max_iso
				walker.current_vert = tvmap[walker.current_vert].max_vid

			walkers_stalled = True
			for walker in reebwalkers.walkers:
				walkers_stalled = walker.done and walkers_stalled

			#if we have in fact stalled, pick the best candidate by the largest contours collected
			if walkers_stalled:
				maxcontourcount = 0
				currentwinner = -1
				for wi,walker in enumerate(reebwalkers.walkers):
					if maxcontourcount < len(walker.contour_id_list):
						maxcontourcount = len(walker.contour_id_list)
						currentwinner = wi
				
				if currentwinner == -1:
					currentwinner = 0	#since they all failed, this means they're all empty, so it doesnt matter which one we pick
				reebwalkers.done = True
				reebwalkers.winner = currentwinner
				print("----WALKERS GOT STALLED----")
				print(reebwalkers)
				print("--------")

		#if we reach here, reeb traversal is done, gather the contours and append them to the reeb edge
		reeb_arc_centroids = []
		final_contours = reebwalkers.walkers[reebwalkers.winner].contour_id_list
		for ci in final_contours:
			reeb_arc_centroids.append(contourlist[ci].contour_centroid)
			contourlist[ci].taken = True
		reeb_edge_arcs.append(reeb_arc_centroids)



