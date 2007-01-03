%define name pygossip
%define version 0.1
%define release 1
%define sysvinit pygossip.rc
%define python python2.4
%define progdir /usr/lib/pymilter

Summary: Python GOSSiP distributed domain reputation service
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.gz
License: Python license
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Stuart Gathman <stuart@bmsi.com>
Packager: Stuart D. Gathman <stuart@bmsi.com>
Url: http://bmsi.com/python/pygossip.html

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
%setup

%build
python2.4 setup.py build

%install
python2.4 setup.py install --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES
mkdir -p $RPM_BUILD_ROOT/etc/mail
cp pygossip.cfg $RPM_BUILD_ROOT/etc/mail
# We use same log dir as milter since we also are a mail add-on
mkdir -p $RPM_BUILD_ROOT/var/log/milter
mkdir -p $RPM_BUILD_ROOT/var/run/milter
mkdir -p $RPM_BUILD_ROOT%{progdir}
# AIX requires daemons to *not* fork, sysvinit requires that they do!
%ifos aix4.1
cat >$RPM_BUILD_ROOT%{progdir}/pygossip.sh <<'EOF'
#!/bin/sh
cd /var/log/milter
exec /usr/local/bin/python pygossip.py >>pygossip.log 2>&1
EOF
%else
cat >$RPM_BUILD_ROOT%{progdir}/pygossip.sh <<'EOF'
#!/bin/sh
cd /var/log/milter
exec >>pygossip.log 2>&1
%{python} %{progdir}/pygossip.py &
echo $! >/var/run/milter/pygossip.pid
EOF
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
%endif
chmod a+x $RPM_BUILD_ROOT%{progdir}/pygossip.sh
cp -p pygossip.py $RPM_BUILD_ROOT%{progdir}

# logfile rotation
mkdir -p $RPM_BUILD_ROOT/etc/logrotate.d
cat >$RPM_BUILD_ROOT/etc/logrotate.d/pygossip <<'EOF'
/var/log/milter/pygossip.log {
  copytruncate
  compress
}
EOF

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
%config /etc/mail/pygossip.cfg
%dir %attr(-,mail,mail)/var/run/milter
%dir %attr(-,mail,mail)/var/log/milter
/etc/logrotate.d/pygossip
/etc/rc.d/init.d/pygossip
%{progdir}/pygossip.sh
%{progdir}/pygossip.py
