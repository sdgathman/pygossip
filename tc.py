# Test gossip server by sending queries from command line.
import sys
import time
import gossip
from gossip.client import Gossip

gossip_node = Gossip(test=True)

cmd = sys.argv[1]
if cmd == 'Q':
  domain,qual = sys.argv[2:4]
  umis = gossip.umis(domain+qual,time.time())
  print gossip_node.query(umis,domain,qual)
elif cmd == 'F':
  umis,spam = sys.argv[2:4]
  gossip_node.feedback(umis,spam)
elif cmd == 'R':
  domain,qual = sys.argv[2:4]
  gossip_node.reset(domain,qual)
