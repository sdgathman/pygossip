%define sysvinit pygossip.rc
%define python python2.6
%define pythonbase python
%define progdir /usr/lib/pymilter

Summary: Python GOSSiP distributed domain reputation service
Name: pygossip
Version: 0.7
Release: 2%{dist}
Source0: pygossip-%{version}.tar.gz
License: Python license
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Stuart Gathman <stuart@bmsi.com>
Packager: Stuart D. Gathman <stuart@bmsi.com>
Url: http://bmsi.com/python/pygossip.html
Requires: %{pythonbase}, %{pythonbase}-pymilter, daemonize

%description
Python GOSSiP library and server.
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

%prep
%setup -n pygossip-%{version}

%build
%{python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{python} setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
#grep '.pyc$' INSTALLED_FILES | sed -e 's/c$/o/' >>INSTALLED_FILES
rm -rf $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/etc/mail
cp pygossip.cfg $RPM_BUILD_ROOT/etc/mail
# We use same log dir as milter since we also are a mail add-on
mkdir -p $RPM_BUILD_ROOT/var/log/milter
mkdir -p $RPM_BUILD_ROOT/var/run/milter
mkdir -p $RPM_BUILD_ROOT%{progdir}
mkdir -p $RPM_BUILD_ROOT/etc/rc.d/init.d
cp %{sysvinit} $RPM_BUILD_ROOT/etc/rc.d/init.d/pygossip
ed $RPM_BUILD_ROOT/etc/rc.d/init.d/pygossip <<'EOF'
/^python=/
c
python="%{python}"
.
/^progdir=/
c
progdir="%{progdir}"
.
w
q
EOF

chmod a+x tc.py pygossip*.py
cp -p tc.py pygossip*.py $RPM_BUILD_ROOT%{progdir}

# logfile rotation
mkdir -p $RPM_BUILD_ROOT/etc/logrotate.d
cat >$RPM_BUILD_ROOT/etc/logrotate.d/pygossip <<'EOF'
/var/log/milter/pygossip.log {
  copytruncate
  compress
}
EOF

%post
/sbin/chkconfig --add pygossip

%preun
if [ $1 = 0 ]; then
  /sbin/chkconfig --del pygossip
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%doc README CHANGES COPYING TODO
%defattr(-,root,root)
%config(noreplace) /etc/mail/pygossip.cfg
%dir %attr(-,mail,mail)/var/run/milter
%dir %attr(-,mail,mail)/var/log/milter
/etc/logrotate.d/pygossip
/etc/rc.d/init.d/pygossip
%{progdir}/pygossip.py
%{progdir}/pygossip.py?
%attr(0755,root,root) %{progdir}/pygossip_purge.py
%{progdir}/pygossip_purge.py?
%attr(0755,root,root) %{progdir}/tc.py
%{progdir}/tc.py?

%changelog
* Sat Aug 29 2015 Stuart Gathman <stuart@bmsi.com> 0.7-2
- remove check for pygossip.sh in initscript
- skip check for null read in readline
- noreplace pygossip.cfg

* Sat Aug 29 2015 Stuart Gathman <stuart@bmsi.com> 0.7-1
- Support IPv6 sockets for client and server
- log exceptions with stack trace
- use daemonize for initscript

* Mon Mar 05 2012 Stuart Gathman <stuart@bmsi.com> 0.6-1
- Don't update peer reputation when neither we nor peer are confident of result.

* Fri Nov 05 2010 Stuart Gathman <stuart@bmsi.com> 0.5-3
- Python-2.6

* Fri Nov 05 2010 Stuart Gathman <stuart@bmsi.com> 0.5-2
- Handle missing observations of peer

* Fri Nov 05 2010 Stuart Gathman <stuart@bmsi.com> 0.5-1
- Allow socket reuse for immediate restart
- Command line client tc.py
- Persistent peer reputation

* Wed Oct 31 2007 Stuart Gathman <stuart@bmsi.com> 0.4-1
- Add locking to client to prevent mixing results.
- Add Reset command.

* Sat Mar 17 2007 Stuart Gathman <stuart@bmsi.com> 0.3-1
- Fix server run loop on client disconnect.
- Optional datadir, run from /var/log/milter if pygossip present there.
