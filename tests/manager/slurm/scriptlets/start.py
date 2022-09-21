#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scriptlet to test start is working."""

import sys

import charms.operator_libs_linux.v0.apt as apt
from charms.operator_libs_linux.v1.systemd import service_running
from slurm_server import SlurmServerManager


def test() -> None:
    # Check slurmctld is installed.
    if not _is_slurmctld_installed():
        sys.exit(1)

    # Start slurmctld.
    manager = SlurmServerManager()
    manager.start()

    # Check that service is active.
    if not service_running("slurmctld"):
        sys.exit(1)
    else:
        sys.exit(0)


def _is_slurmctld_installed() -> bool:
    try:
        apt.DebianPackage.from_installed_package("slurmctld")
        return True
    except apt.PackageNotFoundError:
        return False


if __name__ == "__main__":
    test()
