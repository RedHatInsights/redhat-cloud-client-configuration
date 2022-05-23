# Red Hat Cloud Client Configuration

This repository has the configuration files and spec needed to build an RPM that adds autoregistration for `insights` in cloud environments.

## Building of RPM

It is possible to build RPM using (tito)[https://github.com/rpm-software-management/tito]. The project contains configuration file for tito. Thus you can generate RPM simply using following command:

```
tito build --test --rpm --verbose --debug -o /tmp/tito_build --no-cleanup
```