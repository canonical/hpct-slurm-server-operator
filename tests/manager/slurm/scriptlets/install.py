#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Scriptlet to test install is working."""

import charms.operator_libs_linux.v0.apt as apt
from slurm_server import SlurmServerManager


def test() -> None:
    # Install slurmctld.
    manager = SlurmServerManager()
    manager.install()

    # Test that package is present on system
    try:
        slurmctld = apt.DebianPackage.from_installed_package("slurmctld")
        print(True)
    except apt.PackageNotFoundError:
        print(False)


if __name__ == "__main__":
    test()
