# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

# $Log$
# Revision 1.6  2006/12/27 18:51:02  customdesigned
# Make Observations.__setstate__ compatible with old format.
#
# Revision 1.5  2006/12/27 04:08:26  customdesigned
# Server running in pymilter again.
#
# Revision 1.4  2006/12/27 00:22:45  customdesigned
# Initial peer implementation.
#
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

MAX_PEER_OBS = 100

class Peer(object):

  def __init__(self,host,port):
    self.obs = server.Observations(MAX_PEER_OBS)
    self.client = client.Gossip(host,port)

  def query(self,umis,id,qual,ttl):
    res = self.client.query(umis,id,qual,ttl)
    p_umis,rep,cfi = res[2].split(',')
    assert p_umis == umis
    self.rep = int(rep)
    self.cfi = int(cfi)
    return self.rep,self.cfi

  def is_me(self,connect_ip):
    iplist = self.client.get_iplist()
    print connect_ip,iplist
    return connect_ip in iplist

  def assess(self,rep,cfi):
    "Compare most recent opinion with our opinion and update reputation"
    if self.cfi >= 1 and int(cfi) >= 1:
      # disagreed
      if self.rep > 0 and rep < 0:
	self.obs.setspam(1)
      elif self.rep < 0 and rep > 0:
	self.obs.setspam(1)
      # agreed
      elif self.rep > 0 and rep > 0:
	self.obs.setspam(-1)
      elif self.rep < 0 and rep < 0:
	self.obs.setspam(-1)
      # unsure
      else:
	self.obs.setspam(0)
    else:
      self.obs.setspam(0)
    p_rep = self.obs.reputation()
    p_res = self.rep * self.cfi/100.0
    # should peer reputation affect message cfi instead of res?
    if p_rep < 0:
      p_res *= -p_rep/100.0
    return p_res,self.cfi

def average(l):
  sum,sum2 = 0,0
  for x,y in l:
    sum += x
    sum2 += y
  n = len(l)
  return sum/n,sum2/n

def aggregate(agg):
  "Aggregate reputation and confidence scores"
  avg,avg2 = average((rep,rep * rep) for rep,cfi in agg)
  var = avg2 - avg * avg	# variance
  n = len(agg)
  stddev = math.sqrt(var * n / (n - 1))	# sample standard deviation
  # remove outliers (more than 3 * stddev from mean) and return means
  return average((rep,cfi) for rep,cfi in agg if abs(rep - avg)/stddev <= 3)

class Observations(object):
  "Record up to maxobs observations of an id."
  __slots__ = (
    'bptr','bcnt','hcnt','ncnt','maxobs','firstseen','lastseen','obs','null')

  def __getstate__(self):
    return self.bptr,self.bcnt,self.hcnt,self.ncnt,self.maxobs,	\
      self.firstseen,self.lastseen,self.obs,self.null

  def __setstate__(self,s):
    try:
      self.bptr,self.bcnt,self.hcnt,self.ncnt,self.maxobs, \
	self.firstseen,self.lastseen,self.obs,self.null = s
    except ValueError:	# old format
      self.bptr = s['bptr']
      self.bcnt = s['bcnt']
      self.hcnt = s['hcnt']
      self.firstseen = s['firstseen']
      self.lastseen = s['lastseen']
      self.obs = s['obs']
      self.maxobs = MAXOBS
      self.ncnt = 0
      self.null = 0L

  def __init__(self,maxobs=MAXOBS):
    self.bptr = 0
    self.bcnt = 0	# observation count
    self.hcnt = 0	# cached ham count
    self.ncnt = 0	# cached null count
    self.maxobs = maxobs
    now = time.time()
    self.firstseen = now
    self.lastseen = now
    self.obs = 0L
    self.null = 0L

  def ok(self):
    "Return true if internally consistent"
    if self.hcnt == count_ones(self.obs & ~self.null) \
    	and self.ncnt == count_ones(self.null) \
	and 0 <= self.bptr < self.maxobs \
	and 0 <= self.ncnt + self.hcnt <= self.bcnt:
      return True
    print "%s ncnt=%d obs=%d null=%d"%(self,self.ncnt,
    	count_ones(self.obs & ~self.null),count_ones(self.null))
    return False

  def __str__(self):
    return "%d:%d:%s" % (
      self.hcnt,self.bcnt - self.hcnt - self.ncnt,time.ctime(self.lastseen))

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
    #N = float(self.maxobs)
    N = float(n)
    k = 2
    ham = self.hcnt
    spam = n - ham - self.ncnt
    log.info("ham: %d, spam: %d"%(ham, spam))
    ph =  ham / N
    ps = spam / N

    log.debug("P(h) = %f   P(s) = %f"%(ph, ps))
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
    N = float(self.maxobs)
    epoch = self.firstseen
    now = time.time()
    if now <= epoch:
      return 0.0
    age = 100.0 * (self.lastseen - epoch) / (now - epoch)
    return self.bcnt / N * age

  def setspam(self,v):
    """Add spam status to observation cache.
	v = 1	not spam
	v = 0	N/A
	v = -1	spam

	Examples:
	>>> c = Observations(3)
	>>> c.setspam(-1); c.hcnt,c.bcnt,c.ncnt
	(0, 1, 0)
	>>> c.setspam(1); c.hcnt,c.bcnt,c.ncnt
	(1, 2, 0)
	>>> c.setspam(0); c.hcnt,c.bcnt,c.ncnt
	(1, 3, 1)
	>>> c.setspam(1); c.hcnt,c.bcnt,c.ncnt
	(2, 3, 1)
    """
    thisbit = 1L<<self.bptr
    prev = not (self.obs & thisbit)	# slot was previously spam
    notnull = not (self.null & thisbit)
    if v < 0:
      self.hcnt -= not prev and notnull
      self.ncnt -= not notnull
      self.obs &= ~thisbit
      self.null &= ~thisbit
    elif v > 0:
      self.hcnt += prev or not notnull
      self.ncnt -= not notnull
      self.obs |= thisbit
      self.null &= ~thisbit
    else:
      self.hcnt -= not prev and notnull
      self.null |= thisbit
      self.ncnt += notnull
      
    self.bptr += 1
    if self.bptr >= self.maxobs:
      self.bptr=0  
    if self.bcnt < self.maxobs:
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

  def remove(self,umis):
    "Return (and remove) id corresponding to umis, or None"
    rh = self.hashtab.pop(umis,None)
    if rh:
      self.rseen[rh.ptr] = None
      return rh.id
    return None

  def seen(self,umis):
    "Return True if umis was recently seen."
    if self.hashtab.get(umis,None):
      return True
    return False

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

  def __init__(self,dbname,size,threshold=(-50,1)):
    self.dbp = shelve.open(dbname,'c')
    self.cirq = CircularQueue(size)
    self.lock = thread.allocate_lock()
    self.peers = []
    self.minrep, self.mincfi = threshold

  def query(self,umis,id,qual,ttl,connect_ip=None):

    # find/create database record for id.
    self.lock.acquire()
    try:
      dbp = self.dbp
      id = id + ':' + qual
      if not dbp.has_key(id):
	op = Observations()
	dbp[id] = op
	dbp.sync()
	new = True
      else:
	op = dbp[id]
	new = False
    finally:
      self.lock.release()
    if new:
      log.info("ID %s stored." % id)
    else:
      log.info("ID %s already in db." % id)

    # compute reputation and confidence based on the data for this ID.
    rep = op.reputation()
    cfi = op.confidence()
    log.info("reputation score is: %f,%f"%(rep,cfi))

    # See how peers, if any, feel about id.
    if ttl > 0 and self.peers:
      if self.cirq.seen(umis):
	# already answered for this umis, exclude ourselves.  Intended
	# to prevent query loops.  Should also compare connect ip
	# (FIXME: how to get?) to peers.
        agg = []
      else:
	agg = [(rep,cfi)]
      # FIXME: need to query peers asyncronously
      for peer in self.peers:
        if peer.is_me(connect_ip): continue
        peer.query(umis,id,qual,ttl-1)
	agg.append(peer.assess(rep,cfi))
      rep,cfi = aggregate(agg)

    if not self.cirq.seen(umis):
      self.cirq.add(umis,id)

    # Decide whether to send a reject or a header.
    # Give the person deploying an option to never send a reject, but always
    # a header.  Otherwise, have a threshhold of reputation below which
    # rejects are sent instead of headers.
    if rep < self.minrep and cfi > self.mincfi:
      res = 'REJECT'
    else:
      res = 'PREPEND'
    return res,'X-GOSSiP',"%s,%d,%d" % (umis,rep,cfi)
    # I should also append a comma, the rep score, comma, the confidence

  def feedback(self,umis,spam):
    "Set the spam status of a recently seen umis."
    key = self.cirq.remove(umis)
    if key:
      log.debug("rec'd umis for feedback...%s"%umis)
      if spam == 'Yes':
	vote = -1
      elif spam == 'No':
	vote = 1
      else:
	vote = int(spam) * -2 + 1
      dbp = self.dbp
      self.lock.acquire()
      try:
	try:
	  op = dbp[key]
	  new = False
	except KeyError:
	  op = Observations()
	  new = True
	op.setspam(vote)
	dbp[key] = op
	dbp.sync()
      finally:
	self.lock.release()
      if new:
	log.debug("new data stored: %s"%op)
    else:
      log.info("UMIS not in hash table: %s",umis)

  def do_request(self,buf,connect_ip=None):
    # Get input from SSL connection, store info in rep db if not already there.
    buf = buf.strip()
    log.info(buf)
    e = buf.split(':')
    qtype = e[0]
    if qtype == 'Q':
      a,b,c,umis = e[1:5]
      ttl = int(c)
      resp = '%s %s: %s' % self.query(umis,a,b,ttl,connect_ip)
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

if __name__ == '__main__':
  import doctest, server
  doctest.testmod(server)
