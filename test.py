# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import unittest
import doctest
import random
import gossip.server
import gossip.GossipServer
import socket
from multiprocessing import Process
import logging
import sys
import time

logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='%(asctime)s [%(thread)s] %(message)s',
        datefmt='%Y%b%d %H:%M:%S'
)

db = 'test.db'

def runServer(db,ghost,port):
  gport = int(port)
  try:
    print 'db:',db,'host:',ghost,'port:',gport
    svr = gossip.server.Gossip(db,10)
    print 'server init'
    server = gossip.GossipServer.Daemon(svr,addr=ghost,port=gport)
    signal.signal(signal.SIGTERM,lambda x,y: sys.exit(0))
    print 'server startup'
    server.run()
  except socket.error,x:
    gossip.server.log.error(x)
  except SystemExit: pass
  print 'server shutdown'

class GossipTestCase(unittest.TestCase):

  def testObservations(self):
    os = gossip.server.Observations()
    for i in xrange(100): os.setspam(-1)
    self.assertEqual(os.bcnt,100)
    self.assertEqual(os.hcnt,0)
    for i in xrange(100): os.setspam(1)
    self.assertEqual(os.bcnt,200)
    self.assertEqual(os.hcnt,100)
    for i in xrange(1000): os.setspam(1)
    self.assertEqual(os.bcnt,gossip.server.MAXOBS)
    self.assertEqual(os.hcnt,gossip.server.MAXOBS)
    for i in xrange(100): os.setspam(-1)
    self.assertEqual(os.bcnt,gossip.server.MAXOBS)
    self.assertEqual(os.hcnt,gossip.server.MAXOBS-100)
    for i in xrange(50): os.setspam(0)
    self.assertEqual(os.bcnt,gossip.server.MAXOBS)
    self.assertEqual(os.hcnt,gossip.server.MAXOBS-150)
    self.assertEqual(os.ncnt,50)
    for i in xrange(2000):
      os.setspam(random.randint(-1,1))
    self.assertTrue(os.ok())

  def testAggregate(self):
    data = (
      (100,20), (100,7), (94,16), (90,31), (90,20), (88,24), (86,7),
      (83,6), (83,30), (80,66), (80,5), (77,43), (74,43), (70,23),
      (69,64), (67,6), (56,18)
    )
    wmean,meanw,wvar = gossip.server.weighted_stats(data)
    self.assertEqual(79.5,round(wmean,2))
    self.assertEqual(109.97,round(wvar * 17 / 16,2))
    wavg,avgw = gossip.server.weighted_average(data)
    self.assertEqual(wavg,wmean)
    self.assertEqual(avgw,meanw)
    # nothing thrown out with above dataset
    wavg,avgw = gossip.server.aggregate(data)
    self.assertEqual(wavg,wmean)
    self.assertEqual(avgw,meanw)

  def testConfidence(self):
    # lonely low confidence scores thrown out
    data = ( (76,10), (0,0.5) )
    self.assertEquals((76.0,10.0),gossip.server.aggregate(data))
    # all zero confidence presents a unique problem (sum of weights = 0)
    data = ( (76,0), (0,0) )
    self.assertEquals((38.0,0.0),gossip.server.aggregate(data))


  def testServer(self):
    host = '127.0.0.1'
    port = 11900
    umis = 'FIDDLEDYSTICKS'
    # run GossipServer in Process
    p = Process(target=runServer,args=('test1.db',host,str(port)))
    try:
      p.start()
      time.sleep(2)

      # test subprocess server with gossip.client
      gossip_node = gossip.client.Gossip(host,port)
      res = gossip_node.query(umis,'example.com','SPF',1)
      self.assertEqual(res[0],'PREPEND')
      self.assertEqual(res[2].split(',')[0],umis)

      # set subprocess as Peer for local process
      loc_svr = gossip.server.Gossip('test2.db',10)
      loc_svr.peers.append(gossip.server.Peer('127.0.0.1',11900))

      # query local process server, with depth 1 to query peer also
      res = loc_svr.query(umis,'example.com','SPF',2)
      self.assertEqual(res[0],'PREPEND')
      self.assertEqual(res[2].split(',')[0],umis)

      # terminate peer
    finally:
      p.terminate()
      p.join()

    # query local process server to test error handling
    res = loc_svr.query(umis,'example.com','SPF',1)
    self.assertEqual(res[0],'PREPEND')
    self.assertEqual(res[2].split(',')[0],umis)

def suite():
  s = unittest.makeSuite(GossipTestCase,'test')
  s.addTest(doctest.DocTestSuite(gossip.server))
  return s

if __name__ == '__main__':
  try: os.remove('test.db')
  except: pass
  unittest.TextTestRunner().run(suite())
