Name:           redhat-cloud-client-configuration
Version:        1
Release:        1%{?dist}
Summary:        Red Hat cloud client configuration
License:        GPL-2.0-or-later
URL:            https://github.com/RedHatInsights/redhat-cloud-client-configuration

# Sources can be obtained by
# git clone https://github.com/rpm-software-management/tito
# cd tito
# tito build --tgz
Source0: %{name}-%{version}.tar.gz
Source1: insights-register.service.in
Source2: insights-unregister.path.in
Source3: insights-unregister.service.in
Source4: 80-insights-register.preset
Source5: insights-unregistered.path.in
Source6: insights-unregistered.service.in
Source7: rhcd.path.in
Source8: rhcd-stop.path.in
Source9: rhcd-stop.service.in
Source10: 80-rhcd-register.preset
Source11: insights-register-cgroupv1.service.in
Source12: insights-register.path.in
Source13: rhccc-disable-rhui-repos.py
Source14: rhccc-disable-rhui-repos.service.in
Source15: 80-rhccc-disable-rhui-repos.preset

Source100: LICENSE

BuildArch:      noarch

Requires:      insights-client
Requires:      subscription-manager

%if 0%{?rhel} >= 8 || 0%{?fedora}
Requires:      rhc
%endif

Conflicts: %{name}-cdn

BuildRequires: systemd

%description
Configure client autoregistration for cloud environments


%package cdn
Summary: Red Hat cloud client configuration - CDN

Requires:      insights-client
Requires:      subscription-manager
%if 0%{?rhel} >= 8 || 0%{?fedora}
Requires:      rhc
%endif
Conflicts: %{name}

%description cdn
Configure client autoregistration for cloud environments, connecting directly
to Red Hat's CDN.


%prep
# we have no source


%build
# insights-client
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE12} > insights-register.path
%if 0%{?rhel} >= 8 || 0%{?fedora}
sed -e 's|@bindir@|%{_bindir}|g' %{SOURCE1} > insights-register.service
%else
sed -e 's|@bindir@|%{_bindir}|g' %{SOURCE11} > insights-register.service
%endif
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE2} > insights-unregister.path
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' -e 's|@bindir@|%{_bindir}|g' %{SOURCE3} > insights-unregister.service
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE5} > insights-unregistered.path
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE6} > insights-unregistered.service
sed -e 's|@libexecdir@|%{_libexecdir}|g' %{SOURCE14} > rhccc-disable-rhui-repos.service

%if 0%{?rhel} >= 8 || 0%{?fedora}
# rhcd
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE7} > rhcd.path
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE8} > rhcd-stop.path
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE9} > rhcd-stop.service
%endif

%install
# insights-client
install -d %{buildroot}%{_unitdir}
install -m644 insights-register.path    %{buildroot}%{_unitdir}/
install -m644 insights-register.service %{buildroot}%{_unitdir}/
install -m644 insights-unregister.path    %{buildroot}%{_unitdir}/
install -m644 insights-unregister.service %{buildroot}%{_unitdir}/
install -m644 insights-unregistered.path %{buildroot}%{_unitdir}/
install -m644 insights-unregistered.service %{buildroot}%{_unitdir}/
install -m644 rhccc-disable-rhui-repos.service %{buildroot}%{_unitdir}/
install -d %{buildroot}%{_presetdir}
install -m644 %{SOURCE4} -t %{buildroot}%{_presetdir}/

install -d %{buildroot}%{_libexecdir}
install %{SOURCE13} %{buildroot}%{_libexecdir}
install -m644 %{SOURCE15} -t %{buildroot}%{_presetdir}/

%if 0%{?rhel} >= 8 || 0%{?fedora}
# rhcd
install -D -m644 rhcd.path %{buildroot}%{_unitdir}/
install -D -m644 rhcd-stop.path %{buildroot}%{_unitdir}/
install -D -m644 rhcd-stop.service %{buildroot}%{_unitdir}/
install -m644 %{SOURCE10} -t %{buildroot}%{_presetdir}/
%endif

%post
# insights-client
%systemd_post insights-register.path
%systemd_post insights-unregister.path
%systemd_post insights-unregistered.path
# rhcd
%if 0%{?rhel} >= 8 || 0%{?fedora}
%systemd_post rhcd.path
%systemd_post rhcd-stop.path
%endif

# Make sure that rhsmcertd.service is enabled and running
%systemd_post rhsmcertd.service
# Run following block only during installation (not during update)
if [ $1 -eq 1 ]; then
    # Try to get current value of auto-registration in rhsm.conf
    subscription-manager config --list | grep -q '^[ \t]*auto_registration[ \t]*=[ \t]*1'
    if [ $? -eq 0 ]; then
        auto_reg_enabled=1
    else
        auto_reg_enabled=0
    fi

    # Try to get current value of manage_repos
    subscription-manager config --list | grep -q '^[ \t]*manage_repos[ \t]*=[ \t]*0'
    if [ $? -eq 0 ]; then
        manage_repos_enabled=0
    else
        manage_repos_enabled=1
    fi

    # When we are going to change any configuration value, then save original rhsm.conf
    if [ $auto_reg_enabled -eq 0 -o $manage_repos_enabled -eq 1 ]; then
        echo -e "#\n# Automatic backup of rhsm.conf created by %{name} installation script\n#\n" \
            > /etc/rhsm/rhsm.conf.cloud_save
        cat /etc/rhsm/rhsm.conf >> /etc/rhsm/rhsm.conf.cloud_save
    fi

    # Enable auto-registration in rhsm.conf
    if [ $auto_reg_enabled -eq 0 ]; then
        subscription-manager config --rhsmcertd.auto_registration=1
    fi

    # Disable management of redhat.repo on systems running in
    # public cloud, because content is provided by RHUI
    if [ $manage_repos_enabled -eq 1 ]; then
        subscription-manager config --rhsm.manage_repos=0
    fi

    # Restart rhsmcertd to reload configuration file, when it is necessary
    if [ $auto_reg_enabled -eq 0 -o $manage_repos_enabled -eq 1 ]; then
        /bin/systemctl restart rhsmcertd.service
    fi
fi

%preun
if [ $1 -eq 0 ]; then
    # Packager removal, unmask register if exists
    /bin/systemctl unmask --now insights-register.path > /dev/null 2>&1 || :
%if 0%{?rhel} >= 8 || 0%{?fedora}
    /bin/systemctl unmask --now rhcd.path > /dev/null 2>&1 || :
%endif
fi
%systemd_preun insights-register.path
%systemd_preun insights-unregister.path
%systemd_preun insights-unregistered.path

%if 0%{?rhel} >= 8 || 0%{?fedora}
%systemd_preun rhcd.path
%systemd_preun rhcd-stop.path
%endif

%postun
%systemd_postun insights-register.path
%systemd_postun insights-unregister.path
%systemd_postun insights-unregistered.path

%if 0%{?rhel} >= 8 || 0%{?fedora}
%systemd_postun rhcd.path
%systemd_postun rhcd-stop.path
%endif


# Run following block only during removal (not during update)
if [ $1 -eq 0 ]; then
    if [ -f /etc/rhsm/rhsm.conf.cloud_save ]; then
        rhsmcertd_restart_required=0

        # When auto-registration was originally disabled and we had
        # to enable it during installation of this RPM, then disable it
        # again during removal of RPM package to restore original state.
        grep -q '^[ \t]*auto_registration[ \t]*=[ \t]*0' /etc/rhsm/rhsm.conf.cloud_save
        if [ $? -eq 0 ]; then
            subscription-manager config --rhsmcertd.auto_registration=0
            rhsmcertd_restart_required=1
        fi

        # When managing was originally enabled, then enable it again
        grep -q '^[ \t]*manage_repos[ \t]*=[ \t]*1' /etc/rhsm/rhsm.conf.cloud_save
        if [ $? -eq 0 ]; then
            subscription-manager config --rhsm.manage_repos=1
            rhsmcertd_restart_required=1
        fi

        # Restart rhsmcertd to propagate change in rhsm.conf
        if [ $rhsmcertd_restart_required -eq 1 ]; then
            %systemd_postun_with_restart rhsmcertd.service
        fi

        # Script should clean up after itself
        rm -f /etc/rhsm/rhsm.conf.cloud_save
    fi
fi


%files
%{_presetdir}/80-insights-register.preset
%if 0%{?rhel} >= 8 || 0%{?fedora}
%{_presetdir}/80-rhcd-register.preset
%endif
%{_unitdir}/insights-register.path
%{_unitdir}/insights-register.service
%{_unitdir}/insights-unregister.path
%{_unitdir}/insights-unregister.service
%{_unitdir}/insights-unregistered.path
%{_unitdir}/insights-unregistered.service
%if 0%{?rhel} >= 8 || 0%{?fedora}
%{_unitdir}/rhcd-stop.path
%{_unitdir}/rhcd-stop.service
%{_unitdir}/rhcd.path
%endif


%post cdn
# insights-client
%systemd_post insights-register.path
%systemd_post insights-unregister.path
%systemd_post insights-unregistered.path
%systemd_post rhccc-disable-rhui-repos.service
# rhcd
%if 0%{?rhel} >= 8 || 0%{?fedora}
%systemd_post rhcd.path
%systemd_post rhcd-stop.path
%endif

# Make sure that rhsmcertd.service is enabled and running
%systemd_post rhsmcertd.service
# Tell RHUI to disable itself, if possible: at this point RHUI might
# not be installed yet, so this will fail in that case;
# the firstboot script will disable RHUI again anyway
touch /var/lib/rhui/disable-rhui || :
# Run following block only during installation (not during update)
if [ $1 -eq 1 ]; then
    # Try to get current value of auto-registration in rhsm.conf
    subscription-manager config --list | grep -q '^[ \t]*auto_registration[ \t]*=[ \t]*1'
    if [ $? -eq 0 ]; then
        auto_reg_enabled=1
    else
        auto_reg_enabled=0
    fi

    # When we are going to change any configuration value, then save original rhsm.conf
    if [ $auto_reg_enabled -eq 0 ]; then
        echo -e "#\n# Automatic backup of rhsm.conf created by %{name}-cdn installation script\n#\n" \
            > /etc/rhsm/rhsm.conf.cloud_save
        cat /etc/rhsm/rhsm.conf >> /etc/rhsm/rhsm.conf.cloud_save
    fi

    # Enable auto-registration in rhsm.conf
    if [ $auto_reg_enabled -eq 0 ]; then
        subscription-manager config --rhsmcertd.auto_registration=1
    fi

    # Restart rhsmcertd to reload configuration file, when it is necessary
    if [ $auto_reg_enabled -eq 0 ]; then
        /bin/systemctl restart rhsmcertd.service
    fi
fi

%preun cdn
if [ $1 -eq 0 ]; then
    # Packager removal, unmask register if exists
    /bin/systemctl unmask --now insights-register.path > /dev/null 2>&1 || :
%if 0%{?rhel} >= 8 || 0%{?fedora}
    /bin/systemctl unmask --now rhcd.path > /dev/null 2>&1 || :
%endif
fi
%systemd_preun insights-register.path
%systemd_preun insights-unregister.path
%systemd_preun insights-unregistered.path
%systemd_preun rhccc-disable-rhui-repos.service

%if 0%{?rhel} >= 8 || 0%{?fedora}
%systemd_preun rhcd.path
%systemd_preun rhcd-stop.path
%endif

%postun cdn
%systemd_postun insights-register.path
%systemd_postun insights-unregister.path
%systemd_postun insights-unregistered.path
%systemd_postun rhccc-disable-rhui-repos.service

%if 0%{?rhel} >= 8 || 0%{?fedora}
%systemd_postun rhcd.path
%systemd_postun rhcd-stop.path
%endif

rm -f /var/lib/rhui/disable-rhui

# Run following block only during removal (not during update)
if [ $1 -eq 0 ]; then
    if [ -f /etc/rhsm/rhsm.conf.cloud_save ]; then
        rhsmcertd_restart_required=0

        # When auto-registration was originally disabled and we had
        # to enable it during installation of this RPM, then disable it
        # again during removal of RPM package to restore original state.
        grep -q '^[ \t]*auto_registration[ \t]*=[ \t]*0' /etc/rhsm/rhsm.conf.cloud_save
        if [ $? -eq 0 ]; then
            subscription-manager config --rhsmcertd.auto_registration=0
            rhsmcertd_restart_required=1
        fi

        # Restart rhsmcertd to propagate change in rhsm.conf
        if [ $rhsmcertd_restart_required -eq 1 ]; then
            %systemd_postun_with_restart rhsmcertd.service
        fi

        # Script should clean up after itself
        rm -f /etc/rhsm/rhsm.conf.cloud_save
    fi
fi


%files cdn
%{_libexecdir}/rhccc-disable-rhui-repos.py
%{_presetdir}/80-insights-register.preset
%{_presetdir}/80-rhccc-disable-rhui-repos.preset
%if 0%{?rhel} >= 8 || 0%{?fedora}
%{_presetdir}/80-rhcd-register.preset
%endif
%{_unitdir}/insights-register.path
%{_unitdir}/insights-register.service
%{_unitdir}/insights-unregister.path
%{_unitdir}/insights-unregister.service
%{_unitdir}/insights-unregistered.path
%{_unitdir}/insights-unregistered.service
%{_unitdir}/rhccc-disable-rhui-repos.service
%if 0%{?rhel} >= 8 || 0%{?fedora}
%{_unitdir}/rhcd-stop.path
%{_unitdir}/rhcd-stop.service
%{_unitdir}/rhcd.path
%endif


%changelog
* Wed Sep 14 2022 Gael Chamoulaud <gchamoul@redhat.com> - 1-1
- Remove preset files from %post directive

* Tue May 31 2022 Link Dupont <link@redhat.com> - 1-1
- fix up some spec file descriptions
- add override to automatically activate rhcd

* Tue May 17 2022 Alba Hita Catala <ahitacat@redhat.com> - 1-1
- insights-client autoregistration
