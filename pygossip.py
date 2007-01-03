# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import ConfigParser
import SocketServer
import sys
import time
import gossip
import logging

from gossip.GossipServer import Daemon
from gossip.server import Gossip,Peer

REP_DB = "test.db"
RSEEN_MAX = 30

logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        datefmt='%Y%b%d %H:%M:%S'
)

def getaddr(s):
    a = s.rsplit(':',1)
    if len(a) > 1:
      return a[0],int(a[1])
    try:
      return '0.0.0.0',int(a[0])
    except:
      return a[0],11900

def main():
  config_path = ("pygossip.cfg","/etc/mail/pygossip.cfg")

  cp = ConfigParser.ConfigParser(
    { 'port': '11900', 'rep_db': '/var/log/milter/gossip4.db' }
  )
  cp.read(config_path)
  ghost,gport = getaddr(cp.get('gossip','listen'))
  db = cp.get('gossip','rep_db')
  if cp.has_option('gossip','peers'):
    peers = [q.strip() for q in cp.get('gossip','peers').split(',')]
  else:
    peers = []
  svr = Gossip(db,RSEEN_MAX)

  for p in peers:
    host,port = getaddr(p)
    svr.peers.append(Peer(host,port))

  server = Daemon(svr,addr=ghost,port=gport)
  gossip.server.log.info("pygossip startup")
  server.run()
  gossip.server.log.info("pygossip shutdown")

if __name__ == '__main__':
  if len(sys.argv) > 1:
    gossip = Gossip(REP_DB,RSEEN_MAX)
    for ln in open(sys.argv[1]):
      gossip.do_request(ln.strip())
  else:
    main()
