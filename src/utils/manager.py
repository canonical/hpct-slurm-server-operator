#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Set up and manage slurmctld, munge, etc."""

import logging

import apt
import dbus


logger = logging.getLogger(__name__)


class SlurmManager:
    def __init__(self) -> None:
        _bus = dbus.SystemBus()
        _systemd = _bus.get_object(
            "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
        )
        self.systemd = dbus.Interface(_systemd, "org.freedesktop.systemd1.Manager")

    def install(self, knob: str) -> None:
        """Dispatch for installing charm dependencies.

        Args:
            knob (str): Install function to dispatch.
                Options:
                    "slurmctld": SLURM Central Management daemon
        """
        self.cache = apt.Cache()
        dispatch = {"slurmctld": self._install_slurmctld}
        dispatch[knob]()

    def _install_slurmctld(self) -> None:
        """Install the SLURM Central Management Daemon"""
        logger.debug("Installing SLURM Central Management Daemon (slurmctld)")
        slurmctld_pkg = self.cache["slurmctld"]
        slurmctld_pkg.mark_install()
        self.cache.commit()
        logger.debug("slurmctld installed.")

    def enable(self, knob: str) -> None:
        """Dispatch for enabling charmed services.

        Args:
            knob (str): Enable function to dispatch.
                Options:
                    "slurmctld": SLURM Central Management daemon
        """
        dispatch = {"slurmctld": self._enable_slurmctld}
        dispatch[knob]()

    def _enable_slurmctld(self) -> None:
        """Enable slurmctld service."""
        logger.debug("Enabling slurmctld service.")
        self.systemd.EnableUnitFiles(["slurmctld.service"], False, True)
        self.systemd.Reload()
        logger.debug("slurmctld service enabled.")

    def start(self, knob: str) -> None:
        """Dispatch for starting charmed services.

        Args:
            knob (str): Start function to dispatch.
                Options:
                    "slurmctld": SLURM Central Management daemon
        """
        dispatch = {"slurmctld": self._start_slurmctld}
        dispatch[knob]()

    def _start_slurmctld(self) -> None:
        logger.debug("Starting slurmctld service.")
        self.systemd.StartUnit("slurmctld.service", "fail")
        self.systemd.Reload()
        logger.debug("slurmctld service started.")

    def stop(self, knob: str) -> None:
        """Dispatch for stopping charmed services.

        Args:
            knob (str): Stop function to dispatch.
                Options:
                    "slurmctld": SLURM Central Management daemon
        """
        dispatch = {"slurmctld": self._stop_slurmctld}
        dispatch[knob]()

    def _stop_slurmctld(self) -> None:
        logger.debug("Stopping slurmctld service.")
        self.systemd.StopUnit("slurmctld.service", "fail")
        self.systemd.Reload()
        logger.debug("slurmctld service stopped.")
