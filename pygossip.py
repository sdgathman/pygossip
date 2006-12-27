# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import ConfigParser
import SocketServer
import sys
import gossip
import logging

from gossip.SocketServer import Daemon

REP_DB = "test.db"
RSEEN_MAX = 30

logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        datefmt='%Y%b%d %H:%M:%S'
)

def main():
  config_path = ("gossip.cfg","/etc/mail/gossip.cfg")

  cp = ConfigParser.ConfigParser(
    { 'port': '11900', 'rep_db': '/var/log/milter/gossip4.db' }
  )
  cp.read(config_path)
  gport = cp.getint('gossip','port')
  db = cp.get('gossip','rep_db')
  gossip = Gossip(db,RSEEN_MAX)
  server_addr = ('0.0.0.0',gport)

  server = Daemon(addr='0.0.0.0',port=gport,gossip)
  server.run()

if __name__ == '__main__':
  if len(sys.argv) > 1:
    gossip = Gossip(REP_DB,RSEEN_MAX)
    for ln in open(sys.argv[1]):
      gossip.do_request(ln.strip())
  else:
    main()
