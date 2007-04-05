# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

# $Log$
# Revision 1.17  2007/03/30 18:54:27  customdesigned
# Made sourceforge release.
#
# Revision 1.16  2007/01/11 20:31:11  customdesigned
# Another aggregate edge case fixed.
#
# Revision 1.15  2007/01/10 02:20:47  customdesigned
# Doc comments, aggregate edge conditions.
#
# Revision 1.14  2007/01/08 22:57:09  customdesigned
# Handle all zero weight without offset.
#
# Revision 1.13  2007/01/08 22:41:17  customdesigned
# Use offset to handle 0 confidence.
#
# Revision 1.12  2007/01/08 17:59:55  customdesigned
# Use confidence as weight when aggregating scores.
#
# Revision 1.11  2007/01/03 04:06:33  customdesigned
# Beta release.
#
# Revision 1.10  2006/12/31 04:50:16  customdesigned
# Peer working.
#
# Revision 1.9  2006/12/31 02:48:40  customdesigned
# Make sure all of response is sent.
#
# Revision 1.8  2006/12/30 22:07:37  customdesigned
# Testing server and peers.
#
# Revision 1.7  2006/12/30 21:42:48  customdesigned
# Ready to test peer implementation.
#
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
import client
from gossip import log

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

  def __init__(self,host,port=11900):
    self.client = client.Gossip(host,port)
    self.host = host
    self.obs = None

  def query(self,umis,id,qual,ttl):
    res = self.client.query(umis,id,qual,ttl)
    if not res: return None
    p_umis,rep,cfi = res[2].split(',')
    assert p_umis == umis
    self.rep = int(rep)
    self.cfi = int(cfi)
    return self.rep,self.cfi

  def is_me(self,connect_ip):
    "Return true if incoming connection matches this peer."
    iplist = self.client.get_iplist()
    if not connect_ip: return False
    host,port = connect_ip
    return host in iplist

  def assess(self,rep,cfi):
    "Compare most recent opinion with our opinion and update reputation"
    if not self.obs:
      self.obs = Observations(MAX_PEER_OBS)
    obs = self.obs
    if self.cfi >= 1 and int(cfi) >= 1:
      # disagreed
      if self.rep > 0 and rep < 0:
	obs.setspam(-1)
      elif self.rep < 0 and rep > 0:
	obs.setspam(-1)
      # agreed
      elif self.rep > 0 and rep > 0:
	obs.setspam(1)
      elif self.rep < 0 and rep < 0:
	obs.setspam(1)
      # unsure
      else:
	obs.setspam(0)
    else:
      obs.setspam(0)
    p_rep = obs.reputation()	# peer reputation
    p_cfi = obs.confidence()	# confidence in peer reputation
    return p_rep,p_cfi

def weighted_average(l,offset=0):
  """Compute weighted mean, mean weight.

  l      -- A sequence of (value,weight) tuples.
  offset -- An offset added to weight preventing zero
  	    weights from being completely ignored.

  >>> [round(x,1) for x in weighted_average([(10,3),(15,2)],offset=1)]
  [12.1, 2.5]
  >>> weighted_average([(1,2)])
  (1.0, 2.0)
  >>> weighted_average([])
  (0.0, 0.0)
  """
  if not l: return (0.0,0.0)
  sumx,sumw = 0.0,0.0
  for x,w in l:
    w += offset	# shift 0-100 cfi to avoid 0 weight
    sumx += w * x
    sumw += w
  if sumw:
    try:
      return sumx/sumw,sumw/len(l) - offset
    except ZeroDivisionError: pass
  avg,_ = weighted_average([(x,1) for x,w in l])
  return avg,0.0

def weighted_stats(l,offset=0):
  """Compute weighted mean, mean weight, weighted population variance.

  l      -- A sequence of (value,weight) tuples.
  offset -- An offset added to weight preventing zero
  	    weights from being completely ignored.

  >>> [round(x,1) for x in weighted_stats([(10,3),(15,2)])]
  [12.0, 2.5, 6.0]
  >>> weighted_stats([(1,2)])
  (1.0, 2.0, 0.0)
  >>> weighted_stats([])
  (0.0, 0.0, 0.0)
  """
  if not l: return (0.0,0.0,0.0)
  wsum,wsum2,sumw = 0.0,0.0,0.0
  for x,w in l:
    w += offset	# shift 0-100 cfi to avoid 0 weight
    wsum += w * x
    wsum2 += w * x * x
    sumw += w
  if sumw:
    try:
      wmean = wsum / sumw
      meanw = sumw / len(l) - offset
      wvar = wsum2 / sumw - wmean * wmean
      return wmean,meanw,wvar
    except ZeroDivisionError: pass
  avg,_,var = weighted_stats([(x,1) for x,w in l])
  return avg,0.0,var

def aggregate(agg,offset=0):
  """Aggregate reputation and confidence scores.
  >>> [round(x,1) for x in aggregate([(-76.159416,0.219053),(0,0)])]
  [-76.1, 0.2]
  """
  n = len(agg)
  if n < 1: return (0.0,0,0)
  if n == 1: return agg[0]
  wavg,wcfi,wvar = weighted_stats(agg,offset)
  if wvar <= 0: # only one non-zero cfi
    return weighted_average([(rep,cfi) for rep,cfi in agg if cfi > 0])
  stddev = math.sqrt(wvar * n / (n - 1))	# sample standard deviation
  # remove outliers (more than 3 * stddev from mean) and return means
  return weighted_average([(rep,cfi) for rep,cfi in agg
  	if abs(rep - wavg) <= 3*stddev],offset)

class Observations(object):
  """Record up to maxobs observations of an id."""
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
    """Return true if internally consistent."""
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
    """Compute reputation score."""
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
    """Compute confidence score."""
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
  """Remembers the id for the last N umis."""
  def __init__(self,max):
    self.rseen = [None] * max
    self.ptr_rseen = 0
    self.hashtab = {}

  def remove(self,umis):
    """Return (and remove) id corresponding to umis, or None"""
    rh = self.hashtab.pop(umis,None)
    if rh:
      self.rseen[rh.ptr] = None
      return rh.id
    return None

  def seen(self,umis):
    """Return True if umis was recently seen."""
    if self.hashtab.get(umis,None):
      return True
    return False

  def add(self,umis,id):
    """Add umis,id to cache"""
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

  def __init__(self,dbname,qsize,threshold=(-50,1),saveall=False):
    self.dbp = shelve.open(dbname,'c')
    self.cirq = CircularQueue(qsize)
    self.lock = thread.allocate_lock()
    self.peers = []
    self.minrep, self.mincfi = threshold
    self.saveall = saveall

  def get_observations(self,key,max=MAXOBS):
    "Return Observations,newflag for id:qual"
    op = None
    self.lock.acquire()
    try:
      dbp = self.dbp
      try:
        op = dbp[key]
	new = False
      except KeyError:
        if self.saveall:
	  op = Observations(max)	# establish first seen for id
	  dbp[key] = op
	  dbp.sync()
        new = True
    finally:
      self.lock.release()
    return op

  def query(self,umis,id,qual,ttl,connect_ip=None):

    # find/create database record for id.
    key = id + ':' + qual
    op = self.get_observations(key)
    if not op:
      rep,cfi = 0.0,0.0
    else:
      rep = op.reputation()
      cfi = op.confidence()
      log.info("ID %s reputation: %f,%f"%(key,rep,cfi))

    # compute reputation and confidence based on the data for this ID.

    # See how peers, if any, feel about id.
    if ttl > 0 and self.peers:
      if self.cirq.seen(umis):
	# already answered for this umis, exclude ourselves.  Intended
	# to prevent query loops.  Is this really needed?
        agg = []
      else:
	agg = [(rep,cfi)]
      # FIXME: need to query peers asyncronously
      for peer in self.peers:
        if peer.is_me(connect_ip): continue
	try:
          if not peer.obs:
            peer.obs = self.get_observations(peer.host+':PEER',MAX_PEER_OBS)
	  p_res,p_cfi = peer.query(umis,id,qual,ttl-1)
          log.info("Peer %s says %d,%d" % (peer.host,p_res,p_cfi))
	  p_rep,_ = peer.assess(rep,cfi)
          log.info("Peer %s reputation: %f" % (peer.host,p_rep))
	  if p_rep < 0:	# if we don't usually agree with peer
	    p_cfi *= (100+p_rep) / 100.0 # reduce our confidence in result
	  agg.append((p_res,p_cfi))
	except:
          log.exception("Peer %s"%peer.host)
          continue
      if agg:
	rep,cfi = aggregate(agg)

    if not self.cirq.seen(umis):
      self.cirq.add(umis,key)

    # Decide whether to send a reject or a header.
    # Give the person deploying an option to never send a reject, but always
    # a header.  Otherwise, have a threshhold of reputation below which
    # rejects are sent instead of headers.
    if rep < self.minrep and cfi > self.mincfi:
      res = 'REJECT'
    else:
      res = 'PREPEND'
    # append a comma, the rep score, comma, the confidence
    return res,'X-GOSSiP',"%s,%d,%d" % (umis,rep,cfi)

  def feedback(self,umis,spam):
    "Set the spam status of a recently seen umis."
    key = self.cirq.remove(umis)
    if not key:
      log.info("UMIS not found: %s",umis)
      return
    log.info("ID %s feedback: %s"%(key,spam))
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
