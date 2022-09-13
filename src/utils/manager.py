#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Set up and manage slurmctld, munge, etc."""

import logging

import apt
import dbus


logger = logging.getLogger(__name__)


class SlurmManager:

    _SLURMCTLD = "slurmctld"

    def __init__(self) -> None:
        _bus = dbus.SystemBus()
        _systemd = _bus.get_object(
            "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
        )
        self.manager = dbus.Interface(_systemd, "org.freedesktop.systemd1.Manager")

    def install(self, knob: str) -> None:
        """Dispatch for installing charm dependencies.

        Args:
            knob (str): Install function to dispatch.
                Options:
                    "slurmctld": SLURM Central Management daemon
        """
        self.cache = apt.Cache()
        dispatch = {self._SLURMCTLD: self._slurmctld_install}
        dispatch[knob]()

    def _slurmctld_install(self) -> None:
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
        dispatch = {self._SLURMCTLD: self._enable_slurmctld}
        dispatch[knob]()

    def _enable_slurmctld(self) -> None:
        """Enable slurmctld service."""
        logger.debug("Enabling slurmctld service.")
        self.manager.EnableUnitFiles(["slurmctld.service"], False, True)
        self.manager.Reload()
        logger.debug("slurmctld service enabled.")

    def start(self, knob: str) -> None:
        """Dispatch for starting charmed services.

        Args:
            knob (str): Start function to dispatch.
                Options:
                    "slurmctld": SLURM Central Management daemon
        """
        dispatch = {self._SLURMCTLD: self._start_slurmctld}
        dispatch[knob]()

    def _start_slurmctld(self) -> None:
        logger.debug("Starting slurmctld service.")
        self.manager.StartUnit("slurmctld.service", "fail")
        self.manager.Reload()
        logger.debug("slurmctld service started.")

    def stop(self, knob: str) -> None:
        pass

    def _stop_slurmctld(self) -> None:
        logger.debug("Stopping slurmctld service.")
        self.manager.StopUnit("slurmctld.service", "fail")
        self.manager.Reload()
        logger.debug("slurmctld service stopped.")
