#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Set up and manage slurmctld."""

import logging

import charms.operator_libs_linux.v0.apt as apt
from charms.operator_libs_linux.v1.systemd import (
    service_restart,
    service_running,
    service_start,
    service_stop,
)

logger = logging.getLogger(__name__)


class SlurmServerManager:
    def install(self) -> None:
        """Install SLURM central management daemon."""
        try:
            logger.debug("Installing SLURM Central Management Daemon (slurmctld).")
            apt.add_package("slurmctld")
        except apt.PackageNotFoundError:
            logger.error("Could not install slurmctld. Not found in package cache.")
        except apt.PackageError as e:
            logger.error(f"Could not install slurmctld. Reason: {e.message}.")
        finally:
            logger.debug("slurmctld installed.")

    def start(self) -> None:
        """Start SLURM central management daemon."""
        logger.debug("Starting slurmctld service.")
        if not service_running("slurmctld"):
            service_start("slurmctld")
            logger.debug("slurmctld service started.")
        else:
            logger.debug("slurmctld service is already running.")

    def stop(self) -> None:
        """Stop SLURM central management daemon."""
        logger.debug("Stopping slurmctld service.")
        if service_running("slurmctld"):
            service_stop("slurmctld")
            logger.debug("slurmctld service stopped.")
        else:
            logger.debug("slurmctld service is already stopped.")

    def restart(self) -> None:
        """Restart SLURM central management daemon."""
        logger.debug("Restarting slurmctld service.")
        service_restart("slurmctld")
        logger.debug("slurmctld service restarted.")
