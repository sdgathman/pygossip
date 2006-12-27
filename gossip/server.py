# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

# $Log$
# Revision 1.2  2005/12/24 00:43:44  customdesigned
# handle missing umis
#
# Revision 1.1.1.1  2005/11/07 21:17:56  customdesigned
# Python GOSSiP Domain Reputation Service
#

import shelve
import time
import math
import logging
import sys
import array
import thread

log = logging.getLogger('gossip')

MAXOBS=1024

def count_ones(curr):
  """Count 1 bits in number.
  >>> count_ones(0)
  0
  >>> count_ones(12)
  2
  """
  n = 0
  while curr:
    n += 1
    curr &= (curr - 1)
  return n

class Observations(object):
  "Record up to MAXOBS observations of an id."
  def __init__(self):
    self.bptr = 0
    self.bcnt = 0
    self.hcnt = 0	# cached ham count
    now = time.time()
    self.firstseen = now
    self.lastseen = now
    self.obs = 0L

  def __str__(self):
    return "%d:%d:%s" % (
      self.hcnt,self.bcnt - self.hcnt,time.ctime(self.lastseen))

  # The reputation score is represented by the function:
  #                              ((P(h) - P(s))k)
  #                             e
  #Reputation(i) = 200 * ( ------------------------- - 0.5 )
  #                              ((P(h) - P(s))k)
  #                         1 + e
  #
  #Which is essentially the Rasch logistic model.  
  #P(h) is the ratio of ham accounted for within N to the size of N.
  #P(s) is the ratio of spam accounted for within N to the size of N.
  #k is a constant which effectively adjusts the sensitivity of the 
  #  reputation model to small changes in P(h)-P(s).  Recommended
  #  values for k are in the range of 2-10.  As k->0, Reputation(i)
  #  becomes more linear.
  #i is a given identity.

  def reputation(self):
    n = self.bcnt
    if not n: return 0.0
    #N = float(MAXOBS)
    N = float(n)
    k = 2
    ham = self.hcnt
    spam = n - ham
    log.info("ham: %d, spam: %d"%(ham, spam))
    ph =  ham / N
    ps = spam / N

    log.info("P(h) = %f   P(s) = %f"%(ph, ps))
    num =     math.exp(k * (ph - ps))
    denom = 1 + math.exp(k * (ph - ps))

    return 200 * ((num / denom) - 0.5)

  # The confidence score is represented by the function:
  # 
  # Confidence(R(i)) = [ sum(o) / N ] * age
  # 
  # R(i) is the reputation score for a given identity i.
  # sum(o) is the total number of observations stored in the reputation cache.
  # N is the size of the reputation cache.
  # 
  # age is represented by the following function:
  #                  age(o)
  # age = 100 * (  ---------- )
  #                  age(n)
  # 
  # age(n) = seconds since epoch at time of computation.
  # age(o) = seconds since epoch at time of last local transaction with i
  # 
  # This ensures that the confidence value reflects not only the amount
  # of data the node has for a given identity, but how old that data is.
  #
  # NOTE, we take epoch as time identity was first seen

  def confidence(self):
    "compute confidence"
    N = float(MAXOBS)
    epoch = self.firstseen
    now = time.time()
    if now <= epoch:
      return 0.0
    age = 100.0 * (self.lastseen - epoch) / (now - epoch)
    return self.bcnt / N * age

  def setspam(self,v):
    "Add spam status to observation cache."
    thisbit = 2**self.bptr
    prev = not (self.obs & thisbit)
    if v:
      self.hcnt -= not prev
      self.obs &= ~thisbit
    else:
      self.hcnt += prev
      self.obs |= thisbit
    self.bptr += 1
    if self.bptr >= MAXOBS:
      self.bptr=0  
    elif self.bcnt < MAXOBS:
      self.bcnt += 1
    self.lastseen = time.time()

class rhash(object):
  __slots__ = 'umis','id', 'ptr'
  def __init__(self,umis,id,ptr):
    self.umis = umis
    self.id = id
    self.ptr = ptr

class CircularQueue(object):
  "Remembers the id for the last N umis"
  def __init__(self,max):
    self.rseen = [None] * max
    self.ptr_rseen = 0
    self.hashtab = {}

  def lookup(self,umis):
    "Return (and remove) id corresponding to umis, or None"
    rh = self.hashtab.pop(umis,None)
    if rh:
      self.rseen[rh.ptr] = None
      return rh.id
    return None

  def add(self,umis,id):
    "Add umis,id to cache"
    ptr_rseen = self.ptr_rseen
    rseen = self.rseen
    log.debug("rseen[%i] = %s"%(ptr_rseen,rseen[ptr_rseen]))
    # Check to see if we're about to overwrite an existing UMIS in the 
    # circular queue.  If we are, remove its entry in the hash table first.
    rh = rseen[ptr_rseen]
    if rh: 
      try:
        del self.hashtab[rh.umis]
      except KeyError: pass
    rh = rhash(umis,id,ptr_rseen)
    rseen[ptr_rseen] = rh
    self.hashtab[umis] = rh
    ptr_rseen += 1
    if ptr_rseen == len(rseen): ptr_rseen=0
    self.ptr_rseen = ptr_rseen

class Gossip(object):

  def __init__(self,dbname,size):
    self.dbp = shelve.open(dbname,'c')
    self.cirq = CircularQueue(size)
    self.lock = thread.allocate_lock()

  def query(self,umis,id,qual,ttl):
    self.lock.acquire()
    try:
      dbp = self.dbp
      id = id + ':' + qual
      if not dbp.has_key(id):
	op = Observations()
	dbp[id] = op
	log.info("ID %s stored." % id)
      else:
	log.info("ID %s already in db." % id)
	op = dbp[id]

      # Here's where I need to compute reputation and confidence based on the
      # data I have for this ID.
      rep = op.reputation()
      cfi = op.confidence()
      self.cirq.add(umis,id)
    finally:
      self.lock.release()
    log.info("reputation score is: %f,%f"%(rep,cfi))

    # Here, I need to decide whether to send a reject or a header.
    # Give the person deploying an option to never send a reject, but always
    # a header.  Otherwise, have a threshhold of reputation below which
    # rejects are sent instead of headers.
    return 'PREPEND','X-GOSSiP', "%s,%d,%d" % (umis,rep,cfi)
    # I should also append a comma, the rep score, comma, the confidence

  def feedback(self,umis,spam):
    "Set the spam status of a recently seen umis."
    self.lock.acquire()
    try:
      key = self.cirq.lookup(umis)
      if key:
	dbp = self.dbp
	log.debug("rec'd umis for feedback...%s"%umis)
	try:
	  op = dbp[key]
	  new = False
	except KeyError:
	  op = Observations()
	  new = True
	if spam == 'Yes':
	  op.setspam(1)
	elif spam == 'No':
	  op.setspam(0)
	else:
	  op.setspam(int(spam))
	if new:
	  log.debug("new data stored: %s"%op)
	dbp[key] = op
	dbp.sync()
      else:
	log.info("UMIS not in hash table.")
    finally:
      self.lock.release()

  def do_request(self,buf):
    # Get input from SSL connection, store info in rep db if not already there.
    buf = buf.strip()
    log.info(buf)
    e = buf.split(':')
    qtype = e[0]
    if qtype == 'Q':
      a,b,c,umis = e[1:5]
      ttl = int(c)
      resp = '%s %s: %s' % self.query(umis,a,b,ttl)
      log.info(resp)
      return resp
    if qtype == 'F':
      umis,spam = e[1:3]
      self.feedback(umis,spam)
      return None
    if qtype == 'R':
      umis,spam = e[1:3]
      # FIXME: no idea what this is supposed to do
      #self.do_r(umis,spam)
      return None
    raise ValueError('req: '+buf)
