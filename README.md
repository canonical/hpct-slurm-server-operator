# hpct-slurm-server-operator

## Description

A subordinate charm that installs and manages `slurmctld` and `munge` daemons on a principal charm.

## Usage

> See internal xwiki article [here](https://hpc4can.ddns.net/xwiki/bin/view/Users/nuccitheboss/Nucci's%20Howtos/Setup%20HPC%20cluster%20with%20hpct%20charms/).

To deploy:

```
juju deploy ./hpct-slurm-server-operator_ubuntu-22.04-amd64.charm
```

Assuming a `hpct-xxx-principal-operator` has been deployed:

```
juju relate hpct-slurm-server-operator hpct-xxx-principal-operator
```

Assuming a `hpct-slurm-client-operator` has been deployed:

```
juju relate
juju relate 
juju relate 
```

## Relations

`auth-munge` - a provides relation used to serve the primary slurm server's munge key to slurm clients.

`slurm-server-ready` - a requires relation used to connect to a principal charm that provides the relation.

`slurm-compute` - a requires relation used to consume unit information served by slurm clients.

`slurm-controller` - a provides relation used to serve slurm configuration information to slurm clients.

## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines
on enhancements to this charm following best practice guidelines, and
`CONTRIBUTING.md` for developer guidance.
