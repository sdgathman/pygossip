#!/usr/bin/python2.6
# Test gossip server by sending queries from command line.
import sys
import time
import gossip
import gossip.server
import socket
import logging
import os.path
from gossip.client import Gossip
from optparse import OptionParser
from Milter.config import MilterConfigParser

logging.basicConfig(
        stream=sys.stderr, level=logging.INFO,
        format='%(asctime)s %(message)s', datefmt='%Y%b%d %H:%M:%S'
)

gossip_log = logging.getLogger('gossip')

parser = OptionParser(
        usage='usage: %prog [options] [Q|R domain qual] [F UMIS S|H]')
parser.add_option("-s", "--server", dest="host",
                  help="hostname or ip of pygossip server", default="localhost")
parser.add_option("-c", "--config", dest="config",
                  help="read gossip configuration from file",
		  default=None)
parser.add_option("-d", "--datadir", dest="datadir",
                  help="directory of gossip database",
		  default='/var/lib/milter')
parser.add_option("-q", "--query", dest="query", action="append",
                  help="hostname:qual to query", default=[],
                  metavar="DOMAIN:QUAL")
parser.add_option("-r", "--reset", dest="reset", action="append",
                  help="hostname:qual to reset", default=[],
                  metavar="DOMAIN:QUAL")
parser.add_option("-S", "--spam", dest="spam", action="append",
                  help="UMIS", metavar="UMIS", default=[])
parser.add_option("-H", "--ham", dest="ham", action="append",
                  help="UMIS", metavar="UMIS", default=[])
options, args = parser.parse_args()

cp = MilterConfigParser({
  'server': options.host,
  'datadir': options.datadir
})

if options.config:
  cp.read([options.config])
if cp.has_option('gossip','server'):
  server = cp.get('gossip','server')
  host,port = gossip.splitaddr(server)
  gossip_node = gossip.client.Gossip(host,port)
else:
  datadir = cp.getdefault('milter','datadir','')
  gossip_db = os.path.join(datadir,'gossip4.db')
  gossip_node = gossip.server.Gossip(gossip_db,1000)
  for p in cp.getlist('gossip','peers'):
    host,port = gossip.splitaddr(p)
    try:
      gossip_node.peers.append(gossip.server.Peer(host,port))
    except socket.gaierror as x:
      gossip_log.error("gossip peers: %s",x,exc_info=True)
gossip_ttl = cp.getintdefault('gossip','ttl',1)

if len(args) not in (0,3):
  parser.print_help()
else:
  if args:
    cmd = args[0].upper()
    if cmd == 'Q':
      options.query.append(':'.join(args[1:]))
    elif cmd == 'R':
      options.reset.append(':'.join(args[1:]))
    elif cmd == 'F':
      if args[2].upper()[0] in ('S','1','T'):
        options.spam.append(args[1])
      elif args[2].upper()[0] in ('H','0','F'):
        options.ham.append(args[1])
  if options.query or options.ham or options.spam or options.reset:
    for h in options.query:
      domain,qual = h.rsplit(':',1)
      umis = gossip.umis(domain+qual,time.time())
      print gossip_node.query(umis,domain,qual,gossip_ttl)
    for umis in options.ham:
      gossip_node.feedback(umis,'0')
    for umis in options.spam:
      gossip_node.feedback(umis,'1')
    for h in options.reset:
      domain,qual = h.rsplit(':',1)
      gossip_node.reset(domain,qual)
  else:
    parser.print_help()
    sys.exit(2)
