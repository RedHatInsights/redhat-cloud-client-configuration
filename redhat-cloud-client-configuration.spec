Name:           redhat-cloud-client-configuration
Version:        1
Release:        1%{?dist}
Summary:        Red Hat cloud client configuration
License:        GPLv2+
URL:            https://github.com/RedHatInsights/redhat-cloud-client-configuration

Source0: insights-register.path.in
Source1: insights-register.service.in
Source2: insights-unregister.path.in
Source3: insights-unregister.service.in
Source4: 80-insights-register.preset
%if 0%{?rhel} >= 8
Source6: rhcd.path.in
Source7: rhcd-stop.path.in
Source8: rhcd-stop.service.in
%endif

BuildArch:      noarch

Requires:      insights-client
Requires:      subscription-manager

%if 0%{?rhel} >= 8
Requires:      rhc
%endif

BuildRequires: systemd

%description
Configure client autoregistration for cloud environments

%prep
# we have no source


%build
# insights-client
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE0} > insights-register.path
sed -e 's|@bindir@|%{_bindir}|g' %{SOURCE1} > insights-register.service
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE2} > insights-unregister.path
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' -e 's|@bindir@|%{_bindir}|g' %{SOURCE3} > insights-unregister.service

%if 0%{?rhel} >= 8
# rhcd
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE6} > rhcd.path
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE7} > rhcd-stop.path
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE8} > rhcd-stop.service
%endif

%install
# insights-client
install -d %{buildroot}%{_unitdir}
install -m644 insights-register.path    %{buildroot}%{_unitdir}/
install -m644 insights-register.service %{buildroot}%{_unitdir}/
install -m644 insights-unregister.path    %{buildroot}%{_unitdir}/
install -m644 insights-unregister.service %{buildroot}%{_unitdir}/
install -d %{buildroot}%{_presetdir}
install -m644 %{SOURCE4} -t %{buildroot}%{_presetdir}/

%if 0%{?rhel} >= 8
# rhcd
install -D -m644 rhcd.path %{buildroot}%{_unitdir}/
install -D -m644 rhcd-stop.path %{buildroot}%{_unitdir}/
install -D -m644 rhcd-stop.service %{buildroot}%{_unitdir}/
%endif

%post
%systemd_post insights-register.path
%systemd_post insights-unregister.path
%systemd_post 80-insights-register.preset

%if 0%{?rhel} >= 8
%systemd_post rhcd.path
%systemd_post rhcd-stop.path
%endif

# Make sure that rhsmcertd.service is enabled and running
%systemd_post rhsmcertd.service
if [ $1 -eq 1 ]; then
    # Try to get current value of auto-registration in rhsm.conf
    subscription-manager config --list | grep -q '^[ \t]*auto_registration[ \t]*=[ \t]*1'
    if [ $? -eq 0 ]; then
        auto_reg_already_enabled=1
    else
        auto_reg_already_enabled=0
    fi
    if [ $auto_reg_already_enabled -eq 0 ]; then
        # Save original rhsm.conf
        echo -e "#\n# Automatic backup of rhsm.conf created by %{name} installation script\n#\n" \
            > /etc/rhsm/rhsm.conf.cloud_save
        cat /etc/rhsm/rhsm.conf >> /etc/rhsm/rhsm.conf.cloud_save
        # Enable auto-registration in rhsm.conf
        subscription-manager config --rhsmcertd.auto_registration=1
        # Restart rhsmcertd to reload configuration file
        /bin/systemctl restart rhsmcertd.service
    fi
fi

%preun
if [ $1 -eq 0 ]; then
    # Packager removal, unmask register if exists
    /bin/systemctl unmask --now insights-register.path > /dev/null 2>&1 || :
%if 0%{?rhel} >= 8
    /bin/systemctl unmask --now rhcd.path > /dev/null 2>&1 || :
%endif
fi
%systemd_preun insights-register.path
%systemd_preun insights-unregister.path

%if 0%{?rhel} >= 8
%systemd_preun rhcd.path
%systemd_preun rhcd-stop.path
%endif

%postun
%systemd_postun insights-register.path
%systemd_postun insights-unregister.path

%if 0%{?rhel} >= 8
%systemd_postun rhcd.path
%systemd_postun rhcd-stop.path
%endif

if [ $1 -eq 0 ]; then
    if [ -f /etc/rhsm/rhsm.conf.cloud_save ]; then
        # When auto-registration was originally disabled and we had
        # to enable it during installation of this RPM, then disable it
        # again during removal of RPM package to restore original state.
        grep -q '^[ \t]*auto_registration[ \t]*=[ \t]*0' /etc/rhsm/rhsm.conf.cloud_save
        if [ $? -eq 0 ]; then
            subscription-manager config --rhsmcertd.auto_registration=0
            # Restart rhsmcertd to propagate change in rhsm.conf
            %systemd_postun_with_restart rhsmcertd.service
        fi
        # Script should clean up after itself
        rm -f /etc/rhsm/rhsm.conf.cloud_save
    fi
fi


%files
%{_unitdir}/*
%{_presetdir}/*


%changelog
* Tue May 31 2022 Link Dupont <link@redhat.com> - 1-1
- fix up some spec file descriptions
- add override to automatically activate rhcd

* Tue May 17 2022 Alba Hita Catala <ahitacat@redhat.com> - 1-1
- insights-client autoregistration
