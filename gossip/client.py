# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import socket
import thread
from gossip import log

# I've double checked, and the double newline (actually '\012\012') is in 
# gossip.tar.gz at gossip.sourceforge.net.  I wonder if
# they really meant '\r\n' to work like SMTP. 
EOL = '\n\n'

class Gossip(object):
  def __init__(self,host='127.0.0.1',port=11900,test=False):
    self.node = (host,port)

    # in test mode, we purposefully split up req to make sure server
    # can handle it.
    self.test = test
    self.sock = None
    self.buf = ''
    self.persistent = True
    for a in self.get_iplist():
      if a.find(':') >= 0:
	self.addressfamily = socket.AF_INET6
	break
    else:
      self.addressfamily = socket.AF_INET
    self.lock = thread.allocate_lock()

  def get_iplist(self):
    host,port = self.node
    inet = socket.AF_INET,socket.AF_INET6
    return [ addr[0]
      for family,socktype,proto,canon,addr in socket.getaddrinfo(host,None)
        if family in inet ]

  # hopefully a better readline
  def readline(self):
    ssl = self.sock
    buf = self.buf
    pos = buf.find('\n')
    while pos < 0:
      s = ssl.recv(256)
      # FIXME: leave out until we reproduce hang problem
      #if not s: raise EOFError()
      buf += s
      pos = buf.find('\n')
    self.buf = buf[pos+1:]
    return buf[:pos]

  def sendreq(self,req,void=False):
    self.lock.acquire()
    try:
      try:
        sock = self.sock
        if not sock:
          sock = socket.socket(self.addressfamily,socket.SOCK_STREAM)
          sock.connect(self.node)
          self.sock = sock
          self.buf = ''
        if self.test:
          b = len(req)/2
          sock.sendall(req[:b])
          sock.sendall(req[b:])
        else:
          sock.sendall(req)
        buf = None
        if not void:
          while not buf:	# skip empty lines
            buf = self.readline()
        if not self.persistent:
          sock.close()
          self.sock = None
        return buf
      except socket.error,x:
        log.error('%s: %s',self.node[0],x)
        if sock: sock.close()
        self.sock = None
	if self.addressfamily == socket.AF_INET: return None
    finally:
      self.lock.release()
    # try fallback to INET
    log.info('Fallback to IPv4')
    self.addressfamily = socket.AF_INET
    return self.sendreq(req,void)

  def query(self,umis,id,qual,ttl=1):
    req = "Q:%s:%s:%d:%s%s" % (id,qual,ttl,umis,EOL)
    buf = self.sendreq(req)
    if not buf: return None
    umis,hdr,val = buf.strip().split(None,2)
    return umis,hdr.rstrip(':'),val

  def feedback(self,umis,spam):
    req = "F:%s:%s%s" % (umis,spam,EOL)
    self.sendreq(req,void=True)

  def reset(self,id,qual):
    req = "R:%s:%s%s" % (id,qual,EOL)
    self.sendreq(req,void=True)
