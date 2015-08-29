# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import ConfigParser
import SocketServer
import os
import sys
import time
import gossip
import logging
import signal
import socket

from gossip.GossipServer import Daemon
from gossip.server import Gossip,Peer

REP_DB = "test.db"
RSEEN_MAX = 30

logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%Y%b%d %H:%M:%S'
)

def main():
  config_path = ("pygossip.cfg","/etc/mail/pygossip.cfg")

  cp = ConfigParser.ConfigParser(
    { 'port': '11900', 'rep_db': 'gossip4.db', 'qsize': '100' }
  )
  cp.read(config_path)
  if cp.has_option('gossip','datadir'):
    os.chdir(cp.get('gossip','datadir'))
  ghost,gport = gossip.splitaddr(cp.get('gossip','listen'))
  db = cp.get('gossip','rep_db')
  qsize = int(cp.get('gossip','qsize'))
  if cp.has_option('gossip','peers'):
    peers = [q.strip() for q in cp.get('gossip','peers').split(',')]
  else:
    peers = []
  svr = Gossip(db,qsize)

  for p in peers:
    host,port = gossip.splitaddr(p)
    svr.peers.append(Peer(host,port))

  try:
    server = Daemon(svr,addr=ghost,port=gport)
    signal.signal(signal.SIGTERM,lambda x,y: sys.exit(0))
    gossip.server.log.info("pygossip startup")
    server.run()
  except socket.error,x:
    gossip.server.log.error(x)
  except SystemExit: pass
  gossip.server.log.info("pygossip shutdown")

if __name__ == '__main__':
  if len(sys.argv) > 1:
    gossip = Gossip(REP_DB,RSEEN_MAX)
    for ln in open(sys.argv[1]):
      gossip.do_request(ln.strip())
  else:
    main()
