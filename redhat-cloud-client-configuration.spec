Name:           redhat-cloud-client-configuration
Version:        0.1
Release:        1%{?dist}
Summary:        RedHat cloud client configuration
License:        GPLv2+
URL:            https://github.com/RedHatInsights/redhat-cloud-client-configuration

Source0: insights-register.path.in
Source1: insights-register.service.in
Source2: insights-unregister.path.in
Source3: insights-unregister.service.in
Source4: 80-insights-register.preset 

BuildArch:      noarch

Requires:      insights-client
BuildRequires:      systemd

%description
Insights client autoregistration for cloud environments

%prep
# we have no source


%build
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE0} > insights-register.path
sed -e 's|@bindir@|%{_bindir}|g' %{SOURCE1} > insights-register.service
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' %{SOURCE2} > insights-unregister.path
sed -e 's|@sysconfdir@|%{_sysconfdir}|g' -e 's|@bindir@|%{_bindir}|g' %{SOURCE3} > insights-unregister.service

%install
# insights-client
install -d %{buildroot}%{_unitdir}
install -m644 insights-register.path    %{buildroot}%{_unitdir}/
install -m644 insights-register.service %{buildroot}%{_unitdir}/
install -m644 insights-unregister.path    %{buildroot}%{_unitdir}/
install -m644 insights-unregister.service %{buildroot}%{_unitdir}/
install -d %{buildroot}%{_presetdir}
install -m644 %{SOURCE4} -t %{buildroot}%{_presetdir}/

%post
%systemd_post insights-register.path
%systemd_post insights-unregister.path
%systemd_post 80-insights-register.preset

%preun
if [ $1 -eq 0 ]; then
    # Packager removal, unmask register if exists
    /bin/systemctl unmask --now insights-register.path > /dev/null 2>&1 || : 
fi
%systemd_preun insights-register.path
%systemd_preun insights-unregister.path

%postun
%systemd_postun insights-register.path
%systemd_postun insights-unregister.path

%clean
rm -rf %{buildroot}


%files
%{_unitdir}/*
%{_presetdir}/*


%changelog
* Tue May 17 2022 Alba Hita Catala <ahitacat@redhat.com> - 0.1.1
- insights-client autoresitration
