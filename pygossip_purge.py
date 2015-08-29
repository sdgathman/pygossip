#!/usr/bin/python2.6
# Purge ancient records from reputation database.

from __future__ import print_function
import shelve
import gossip
import time
import os
import os.path

def purgedb(name,maxage=90,log=None):
  now = time.time()
  too_old = now - maxage * 24 * 60 * 60;
  newname = name + '.lock'
  if os.path.exists(newname):
    raise IOError('%s already exists' % newname)
  newdb = shelve.open(newname,'c',protocol=2)
  db = shelve.open(name,'r')
  kept = 0
  old = 0
  try:
    changed = False
    for o in db.dict.iterkeys():	# enumerate all identities
      try:
	obs = db[o]	# get observations
	if obs.lastseen >= too_old:
	  newdb[o] = obs
	  kept += 1
	else:
	  old += 1
	  changed = True
          if log:
	    print(o,file=log)
      except: pass	# ignore database inconsistencies
    db.close()
    newdb.close()
    if changed:
      os.rename(name,name+'.bak')
      os.rename(newname,name)
    return kept,old
  except:
    db.close()
    newdb.close()
    raise

with open('gossip_purge.log','wt') as fp:
  if True:
    kept,old = purgedb('gossip4.db',360,log=None)
  else:
    kept,old = purgedb('gossip4.db',360,log=fp)
  print(3,'kept,',4,'purged',file=fp)
