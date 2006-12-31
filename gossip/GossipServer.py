# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import SocketServer
import logging

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

  def send(self,s):
    ssl = self.request
    n = ssl.send(s)
    while n < len(s):
      if n > 0: s = s[n:]
      n = ssl.send(s)

  def handle(self):
    log.debug("connect %s",self.client_address)
    ssl = self.request
    gossip = self.server.gossip
    self.buf = ''
    while True:
      try:
        buf = self.readline()
	if buf == '': break
        resp = gossip.do_request(buf,self.client_address)
	if resp:
	  log.debug(resp)
	  self.send(resp+'\012\012')
      except EOFError:
        log.debug("Ending connection")
	return
      except ValueError:
        log.info("Bad req: "+buf)

class Daemon(object):

  def __init__(self,gossip,addr='0.0.0.0',port=11900):
    self.gossip = gossip
    server_addr = (addr,port)
    self.server = SocketServer.ThreadingTCPServer(server_addr,Handler)
    self.server.daemon = self
    self.server.gossip = gossip

  def run(self):
    self.server.serve_forever()
    #self.server.handle_request()
