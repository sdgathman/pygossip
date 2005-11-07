# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import ConfigParser
import SocketServer
import sys
import gossip
import logging

from gossip.server import Gossip

REP_DB = "test.db"
RSEEN_MAX = 30

logging.basicConfig(
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        datefmt='%Y%b%d %H:%M:%S'
)

log = logging.getLogger('gossip')

class Handler(SocketServer.BaseRequestHandler):

  def readline(self):
    ssl = self.request
    buf = self.buf
    pos = buf.find('\012')
    while pos < 0:
      buf += ssl.recv(256)
      pos = buf.find('\012')
    self.buf = buf[pos+1:]
    return buf[:pos]

  def handle(self):
    log.debug("connect")
    ssl = self.request
    self.buf = ''
    while True:
      try:
        buf = self.readline()
	if buf == '': break
        resp = gossip.do_request(buf)
	if resp:
	  ssl.send(resp+'\012\012')
      except EOFError:
        log.debug("Ending connection")
	return

def main():
  config_path = ("gossip.cfg","/etc/mail/gossip.cfg")

  cp = ConfigParser.ConfigParser(
    { 'port': '11900', 'rep_db': '/var/log/milter/gossip4.db' }
  )
  cp.read(config_path)
  global REP_DB,gossip
  gport = cp.getint('gossip','port')
  REP_DB = cp.get('gossip','rep_db')
  gossip = Gossip(REP_DB,RSEEN_MAX)
  server_addr = ('0.0.0.0',gport)

  server = SocketServer.ThreadingTCPServer(server_addr,Handler)
  server.serve_forever()
  #server.handle_request()

if __name__ == '__main__':
  if len(sys.argv) > 1:
    gossip = Gossip(REP_DB,RSEEN_MAX)
    for ln in open(sys.argv[1]):
      gossip.do_request(ln.strip())
  else:
    main()
