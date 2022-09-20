#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scriptlet to test stop is working."""

import charms.operator_libs_linux.v0.apt as apt
from charms.operator_libs_linux.v1.systemd import service_running
from slurm_server import SlurmServerManager


def test() -> None:
    # Check slurmctld is installed.
    if not _is_slurmctld_installed:
        print(False)
        exit(1)

    # Stop slurmctld.
    manager = SlurmServerManager()
    manager.stop()

    # Check that service is active.
    if service_running("slurmctld"):
        print(False)
        exit(1)
    else:
        print(True)
        exit(0)


def _is_slurmctld_installed() -> bool:
    try:
        slurmctld = apt.DebianPackage.from_installed_package("slurmctld")
        return True
    except apt.PackageNotFoundError:
        return False


if __name__ == "__main__":
    test()
