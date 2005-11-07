# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import unittest
import doctest
import gossip.server

class GossipTestCase(unittest.TestCase):
  def testObservations(self):
    os = gossip.server.Observations()
    for i in xrange(100): os.setspam(1)
    self.assertEqual(os.bcnt,100)
    self.assertEqual(os.hcnt,0)
    for i in xrange(100): os.setspam(0)
    self.assertEqual(os.bcnt,200)
    self.assertEqual(os.hcnt,100)
    for i in xrange(1000): os.setspam(0)
    self.assertEqual(os.bcnt,gossip.server.MAXOBS)
    self.assertEqual(os.hcnt,gossip.server.MAXOBS)
    for i in xrange(100): os.setspam(1)
    self.assertEqual(os.bcnt,gossip.server.MAXOBS)
    self.assertEqual(os.hcnt,gossip.server.MAXOBS-100)

def suite():
  s = unittest.makeSuite(GossipTestCase,'test')
  s.addTest(doctest.DocTestSuite(gossip.server))
  return s

if __name__ == '__main__':
  try: os.remove('test.db')
  except: pass
  unittest.TextTestRunner().run(suite())
