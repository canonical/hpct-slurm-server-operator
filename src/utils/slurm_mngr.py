#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Set up and manage slurmctld."""

import logging

import apt
import dbus


logger = logging.getLogger(__name__)


class SlurmServerManager:
    def __init__(self) -> None:
        _bus = dbus.SystemBus()
        _systemd = _bus.get_object(
            "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
        )
        self.systemd = dbus.Interface(_systemd, "org.freedesktop.systemd1.Manager")

    def install(self) -> None:
        """Install the SLURM Central Management Daemon."""
        logger.debug("Installing SLURM Central Management Daemon (slurmctld)")
        cache = apt.Cache()
        slurmctld_pkg = cache["slurmctld"]
        slurmctld_pkg.mark_install()
        cache.commit()
        logger.debug("slurmctld installed.")

    def enable(self) -> None:
        logger.debug("Enabling slurmctld service.")
        self.systemd.EnableUnitFiles(["slurmctld.service"], False, True)
        self.systemd.Reload()
        logger.debug("slurmctld service enabled.")

    def start(self) -> None:
        logger.debug("Starting slurmctld service.")
        self.systemd.StartUnit("slurmctld.service", "fail")
        self.systemd.Reload()
        logger.debug("slurmctld service started.")

    def stop(self) -> None:
        logger.debug("Stopping slurmctld service.")
        self.systemd.StopUnit("slurmctld.service", "fail")
        self.systemd.Reload()
        logger.debug("slurmctld service stopped.")
