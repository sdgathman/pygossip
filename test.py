# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import unittest
import doctest
import random
import gossip.server

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
    wmean,meanw,wnvar = gossip.server.weighted_stats(data)
    self.assertEqual(79.5,round(wmean,2))
    self.assertEqual(109.97,round(wnvar / 16,2))
    wavg,avgw = gossip.server.weighted_average(data)
    self.assertEqual(wavg,wmean)
    self.assertEqual(avgw,meanw)
    # nothing thrown out with above dataset
    wavg,avgw = gossip.server.aggregate(data)
    self.assertEqual(wavg,wmean)
    self.assertEqual(avgw,meanw)
    # lonely low confidence scores thrown out
    data = ( (76,10), (0,0) )
    self.assertEquals((76.0,10.0),gossip.server.aggregate(data))

def suite():
  s = unittest.makeSuite(GossipTestCase,'test')
  s.addTest(doctest.DocTestSuite(gossip.server))
  return s

if __name__ == '__main__':
  try: os.remove('test.db')
  except: pass
  unittest.TextTestRunner().run(suite())
