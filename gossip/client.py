# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import socket
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

  def get_iplist(self):
    host,port = self.node
    host,aliases,iplist = socket.gethostbyname_ex(host)
    return iplist

  # from smtplib.  I had hoped there was a better way than reading
  # one char at a time.
  def readline1(self):
      str = ""
      chr = None
      ssl = self.sock
      while chr != "\n":
	  chr = ssl.recv(1)
	  str += chr 
      return str

  # hopefully a better readline
  def readline(self):
    ssl = self.sock
    buf = self.buf
    pos = buf.find('\n')
    while pos < 0:
      buf += ssl.recv(256)
      pos = buf.find('\n')
    self.buf = buf[pos+1:]
    return buf[:pos]

  # sock.sendall() gets Broken Pipe exception (why?)
  def sendall(self,s):
    ssl = self.request
    n = ssl.send(s)
    while n < len(s):
      if n > 0: s = s[n:]
      n = ssl.send(s)

  def query(self,umis,id,qual,ttl=1):
    try:
      sock = self.sock
      if not sock:
	sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	sock.connect(self.node)
	self.sock = sock
	self.buf = ''
      req = "Q:%s:%s:%d:%s%s" % (id,qual,ttl,umis,EOL)
      if self.test:
	b = len(req)/2
	sock.sendall(req[:b])
	sock.sendall(req[b:])
      else:
	sock.sendall(req)
      buf = None
      while not buf:	# skip empty lines
        buf = self.readline()
      if not self.persistent:
        sock.close()
	self.sock = None
      return buf.strip().split()
    except socket.error,x:
      log.error('%s: %s',self.node[0],x)
      if sock: sock.close()
      self.sock = None
      return None

  def feedback(self,umis,spam):
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.connect(self.node)
    req = "F:%s:%s%s" % (umis,spam,EOL)
    sock.send(req)
