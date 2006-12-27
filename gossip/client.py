# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import socket

class Gossip(object):

  def __init__(self,host='127.0.0.1',port=11900,test=False):
    self.node = (host,port)
    # in test mode, we purposefully split up req to make sure server
    # can handle it.
    self.test = test

  def query(self,umis,id,qual,ttl=1):
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.connect(self.node)
    req = "Q:%s:%s:%d:%s\012\012" % (id,qual,ttl,umis)
    if self.test:
      b = len(req)/2
      sock.send(req[:b])
      sock.send(req[b:])
    else:
      sock.send(req)
    buf = sock.recv(256)
    return buf.strip().split()

  def feedback(self,umis,spam):
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.connect(self.node)
    req = "F:%s:%s\012\012" % (umis,spam)
    sock.send(req)
