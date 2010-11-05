# Test gossip server by sending queries from command line.
import sys
import time
import gossip
from gossip.client import Gossip
from optparse import OptionParser

#gossip_node = Gossip(test=True)
parser = OptionParser(
        usage='usage: %prog [options] [Q|R domain qual] [F UMIS S|H]')
parser.add_option("-s", "--server", dest="host",
                  help="hostname or ip of pygossip server", default="localhost")
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

gossip_node = Gossip(host=options.host)

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
      print gossip_node.query(umis,domain,qual)
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
