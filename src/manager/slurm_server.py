#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Set up and manage slurmctld."""

import hashlib
import logging
import os
from typing import Union

import charms.operator_libs_linux.v0.apt as apt
from charms.operator_libs_linux.v1.systemd import (
    service_restart,
    service_running,
    service_start,
    service_stop,
)
from hpcteditors.app.slurm import SlurmConfFileEditor
from sysprober.network import Network

logger = logging.getLogger(__name__)


class SlurmServerManagerError(Exception):
    """Raised when the slurm server manager encounters an error."""

    ...


class SlurmServerManager:
    """Top-level manager class for controlling slurmctld on unit."""

    def __init__(self) -> None:
        self.__network = Network()

        self.conf_file = "/etc/slurm/slurm.conf"
        self.hostname = self.__network.info["hostname"]
        for iface in self.__network.info["ifaces"]:
            if iface["name"] == "eth0":
                for addr in iface["info"]["addr_info"]:
                    if addr["family"] == "inet":
                        self.ipv4_address = addr["address"]

    def get_hash(self, file: Union[str, None] = None) -> Union[str, None]:
        """Get the sha224 hash of a file.

        Args:
            str | None: File to hash. Defaults to self.conf_file if file is None.

        Returns:
            str: sha224 hash of the file, or None if file does not exist.
        """
        file = self.conf_file if file is None else file
        return (
            hashlib.sha224(open(file, "rb").read()).hexdigest() if os.path.isfile(file) else None
        )

    def generate_new_conf(self) -> None:
        """Generate a base configuration file for slurm."""
        open("/etc/slurm/slurm.conf", "w").close()
        editor = SlurmConfFileEditor()
        editor.load()
        content = [
            f"SlurmctldHost={self.hostname}({self.ipv4_address})",
            "ClusterName=base",
            "AuthType=auth/munge",
            "FirstJobId=65536",
            "InactiveLimit=120",
            "JobCompType=jobcomp/filetxt",
            "JobCompLoc=/var/log/slurm/jobcomp",
            "ProctrackType=proctrack/linuxproc",
            "KillWait=30",
            "MaxJobCount=10000",
            "MinJobAge=3600",
            "ReturnToService=0",
            "SchedulerType=sched/backfill",
            "SlurmctldLogFile=/var/log/slurm/slurmctld.log",
            "SlurmdLogFile=/var/log/slurm/slurmd.log",
            "SlurmctldPort=7002",
            "SlurmdPort=7003",
            "SlurmdSpoolDir=/var/spool/slurmd.spool",
            "StateSaveLocation=/var/spool/slurm.state",
            "SwitchType=switch/none",
            "TmpFS=/tmp",
            "WaitTime=30",
        ]
        editor.add_lines(content)
        editor.dump()

    def generate_base_partition(self) -> None:
        """Generation a base partition using automatically discovered nodes."""
        conf = [line.strip() for line in open(self.conf_file)]

        node_list = set()
        for entry in conf:
            if entry.startswith("NodeName"):
                lexeme = entry.split(" ")
                token = lexeme[0].split("=")
                node_list.add(token[1])

        for entry in conf:
            if entry.startswith("PartitionName=base"):
                conf.remove(entry)

        conf.append(
            f"PartitionName=base Nodes={','.join(node_list)} MaxNodes={len(node_list)} State=UP"
        )

        open(self.conf_file, "w").close()
        editor = SlurmConfFileEditor()
        editor.load()
        editor.add_lines(conf)
        editor.dump()

    def add_node(self, **kwargs) -> None:
        """Add a new node to the slurm configuration file.

        Raises:
            SlurmServerManagerError: Thrown if a bad configuration is received from a node.
        """
        nodename = kwargs.get("nodename", None)
        nodeaddr = kwargs.get("nodeaddr", None)
        cpus = kwargs.get("cpus", None)
        realmemory = kwargs.get("realmemory", None)
        if None in [nodename, nodeaddr, cpus, realmemory]:
            raise SlurmServerManagerError("Invalid node configuration received.")

        editor = SlurmConfFileEditor()
        editor.load()
        editor.add_line(
            f"NodeName={nodename} NodeAddr={nodeaddr} CPUs={cpus} RealMemory={realmemory}"
        )
        editor.dump()

    def install(self) -> None:
        """Install SLURM central management daemon.

        Raises:
            SlurmServerManagerError: Thrown if slurmctld fails to install.
        """
        try:
            logger.debug("Installing SLURM Central Management Daemon (slurmctld).")
            apt.add_package("slurmctld")
        except apt.PackageNotFoundError:
            logger.error("Could not install slurmctld. Not found in package cache.")
            raise SlurmServerManagerError("Failed to install slurmctld.")
        except apt.PackageError as e:
            logger.error(f"Could not install slurmctld. Reason: {e.message}.")
            raise SlurmServerManagerError("Failed to install slurmctld.")
        finally:
            logger.debug("slurmctld installed.")

    def start(self) -> None:
        """Start SLURM central management daemon.

        Raises:
            SlurmServerManagerError: Thrown if slurmctld is not installed on unit.
        """
        if self.__is_installed():
            logger.debug("Starting slurmctld service.")
            if not service_running("slurmctld"):
                service_start("slurmctld")
                logger.debug("slurmctld service started.")
            else:
                logger.debug("slurmctld service is already running.")
        else:
            raise SlurmServerManagerError("slurmctld is not installed.")

    def stop(self) -> None:
        """Stop SLURM central management daemon.

        Raises:
            SlurmServerManagerError: Thrown if slurmctld is not installed on unit.
        """
        if self.__is_installed():
            logger.debug("Stopping slurmctld service.")
            if service_running("slurmctld"):
                service_stop("slurmctld")
                logger.debug("slurmctld service stopped.")
            else:
                logger.debug("slurmctld service is already stopped.")
        else:
            raise SlurmServerManagerError("slurmctld is not installed.")

    def restart(self) -> None:
        """Restart SLURM central management daemon.

        Raises:
            SlurmServerManagerError: Thrown if slurmctld is not installed on unit.
        """
        if self.__is_installed():
            logger.debug("Restarting slurmctld service.")
            service_restart("slurmctld")
            logger.debug("slurmctld service restarted.")
        else:
            raise SlurmServerManagerError("slurmctld is not installed.")

    def __is_installed(self) -> bool:
        """Internal function to check if slurmctld Debian package is installed on the unit.

        Returns:
            bool: True if Debian package is present; False if Debian package is not present.
        """
        return True if apt.DebianPackage.from_installed_package("slurmctld").present else False
