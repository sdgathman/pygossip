#! /usr/bin/env python2.4
# 
# $Id$
#

import sys,os

sys.path.insert(0,os.getcwd())

from distutils.core import setup

import gossip

setup(
        #-- Package description
        name = 'pygossip',
        license = 'Python license',
        version = '0.7',
        description = 'Python GOSSiP distributed domain reputation service',
        long_description = """Python GOSSiP library and server.
As SPF is implemented, spammers will also adopt SPF.  With forging
under control, the next step is to track the reputation of domains.
GOSSiP tracks the ratio of spam to ham for the last 1000 messages from
each domain, and computes a reputation score from that that ranges 
from -100 to +100.  It also computes a confidence score that increases
from 0 to 100 with the number and freshness of the observations.
It can also check with peers, and combine scores.  Observations are
provided by a spam filter or user feedback.  Pygossip is supported
by pymilter.

See http://gossip-project.sourceforge.net/
    http://pymilter.sourceforge.net/
""",
        author = 'Stuart Gathman', 
        author_email = 'stuart@bmsi.com',
        url = 'http://bmsi.com/python/pygossip.html',
	py_modules = [],
        packages = ['gossip'],
	keywords = ['GOSSiP','reputation','email'],
	classifiers = [
	  'Development Status :: 4 - Beta',
	  'Environment :: No Input/Output (Daemon)',
	  'Intended Audience :: Developers',
	  'Intended Audience :: System Administrators',
	  'License :: OSI Approved :: GNU General Public License (GPL)',
	  'Natural Language :: English',
	  'Operating System :: OS Independent',
	  'Programming Language :: Python',
	  'Topic :: Communications :: Email',
	  'Topic :: Communications :: Email :: Mail Transport Agents',
	  'Topic :: Software Development :: Libraries :: Python Modules'
	]
)
