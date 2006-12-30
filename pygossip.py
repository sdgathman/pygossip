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

def main():
  config_path = ("pygossip.cfg","/etc/mail/pygossip.cfg")

  cp = ConfigParser.ConfigParser(
    { 'port': '11900', 'rep_db': '/var/log/milter/gossip4.db' }
  )
  cp.read(config_path)
  gport = cp.getint('gossip','listen')
  db = cp.get('gossip','rep_db')
  if cp.has_option('gossip','peers'):
    peers = [q.strip() for q in cp.get('gossip','peers').split(',')]
  else:
    peers = []
  svr = Gossip(db,RSEEN_MAX)

  for p in peers:
    a = p.rsplit(':',1)
    if len(a) > 1:
      host,port = a[0],int(a[1])
    else:
      host,port = a[0],11900
    svr.peers.append(Peer(host,port))

  server = Daemon(svr,addr='0.0.0.0',port=gport)
  gossip.server.log.info("pysrs startup")
  server.run()
  gossip.server.log.info("pysrs shutdown")

if __name__ == '__main__':
  if len(sys.argv) > 1:
    gossip = Gossip(REP_DB,RSEEN_MAX)
    for ln in open(sys.argv[1]):
      gossip.do_request(ln.strip())
  else:
    main()
