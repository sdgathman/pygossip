# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import SocketServer
import logging
import socket

log = logging.getLogger('gossip')

class Handler(SocketServer.BaseRequestHandler):

  def readline(self):
    ssl = self.request
    buf = self.buf
    pos = buf.find('\n')
    while pos < 0:
      s = ssl.recv(256)
      if not s: raise EOFError()
      buf += s
      pos = buf.find('\n')
    self.buf = buf[pos+1:]
    return buf[:pos]

  def sendall(self,s):
    ssl = self.request
    n = ssl.send(s)
    while n < len(s):
      if n > 0: s = s[n:]
      n = ssl.send(s)

  def handle(self):
    log.info("connect %s",self.client_address)
    ssl = self.request
    gossip = self.server.gossip
    self.buf = ''
    while True:
      try:
        buf = self.readline()
	if buf == '': continue
	print 'Server:',buf
        resp = gossip.do_request(buf,self.client_address)
	if resp:
	  ssl.sendall(resp+'\n\n')
	else:
          ssl.sendall('\n\n')
      except EOFError:
        log.debug("Ending connection")
	return
      except ValueError:
        log.exception("Bad req: "+buf)

class Daemon(SocketServer.ThreadingTCPServer):

  allow_reuse_address = True

  def __init__(self,gossip,addr='::',port=11900):
    self.gossip = gossip
    server_addr = (addr,port)
    if addr.find(':') >= 0:
      SocketServer.ThreadingTCPServer.address_family = socket.AF_INET6
    SocketServer.ThreadingTCPServer.__init__(self,server_addr,Handler)

  def run(self):
    self.serve_forever()
    #self.server.handle_request()
