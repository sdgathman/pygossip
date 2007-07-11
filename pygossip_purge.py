# Purge ancient records from reputation database.

import shelve
import gossip
import time
import os
import os.path

def purgedb(name,maxage=90):
  now = time.time()
  too_old = now - maxage * 24 * 60 * 60;
  newname = name + '.lock'
  if os.path.exists(newname):
    raise IOError('%s already exists' % newname)
  newdb = shelve.open(newname,'c')
  db = shelve.open(name,'r')
  kept = 0
  old = 0
  try:
    changed = False
    for o in db:		# enumerate all identities
      try:
	obs = db[o]	# get observations
	if obs.lastseen >= too_old:
	  newdb[o] = obs
	  kept += 1
	else:
	  old += 1
	  changed = True
      except: pass	# ignore database inconsistencies
    db.close()
    newdb.close()
    if changed:
      os.rename(newname,name)
    return kept,old
  except:
    db.close()
    newdb.close()
    raise

purgedb('gossip4.db',180)
