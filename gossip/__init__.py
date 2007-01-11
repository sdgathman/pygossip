# Copyright 2005 Business Management Systems, Inc
# Author: Stuart D. Gathman
# Distributed under the terms of the GNU General Public License version 2
# See COPYING for details

import md5
import base64
import logging

log = logging.getLogger('gossip')

__all__ = [ 'umis' ]

__version__ = '0.2'

def umis(id,nonce):
  digest = md5.new(id)
  digest.update(str(nonce))
  return base64.b64encode(digest.digest(),'.$').rstrip('=')
