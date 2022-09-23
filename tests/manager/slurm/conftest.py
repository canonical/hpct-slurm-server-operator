#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Configurations for SlurmServerManager tests."""

from pylxd import Client


def pytest_unconfigure(config) -> None:
    """Teardown LXD test instance."""
    instance = Client().instances.get("test-slurm-server-manager")
    instance.stop(wait=True)
    instance.delete(wait=True)
