#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Set up and manage slurmctld."""

import hashlib
import ipaddress
import logging
import os

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


class InvalidNodeConfError(Exception):
    """Raised when an invalid node configuration is received."""

    def __init__(self, value: object, desc: str = "Invalid value:") -> None:
        self.value = value
        self.desc = desc
        super().__init__(self.desc)

    def __str__(self) -> str:
        """String representation of InvalidNodeConfError."""
        return f"{self.desc} {self.value}"


class SlurmctldNotFoundError(Exception):
    """Raised when trying to perform an operation with slurmctld but slurmctld is not installed."""

    def __init__(self, name: str, desc: str = "Slurmctld is not installed.") -> None:
        self.name = name
        self.desc = desc
        super().__init__(self.desc)

    def __str__(self) -> str:
        """String representation of SlurmctldNotFoundError."""
        return f"{self.desc} Please install slurmctld using {self.name}.install()."


class SlurmConfNotFoundError(Exception):
    """Raised when manager cannot locate the `slurm.conf` file on a unit."""

    def __init__(self, path: str, name: str, desc: str = "slurm.conf not found on host.") -> None:
        self.path = path
        self.name = name
        self.desc = desc
        super().__init__(self.desc)

    def __str__(self) -> str:
        """String representation of SlurmConfNotFoundError."""
        return (
            f"{self.desc} Location searched: {self.path}. "
            f"Generate a new slurm.conf with {self.name}.generate_new_conf()."
        )


class SlurmServerManager:
    """Top-level manager class for controlling slurmctld on unit."""

    def __init__(self) -> None:
        self.__network = Network()

    @property
    def installed(self) -> bool:
        """Installation status of slurmctld.

        Returns:
            bool: True if slurmctld is installed on unit;
            False if slurmctld is not installed on unit.
        """
        return self.__is_installed()

    @property
    def running(self) -> bool:
        """Status of slurmctld daemon.

        Returns:
            bool: True if slurmctld daemon is running;
            False if slurmctld daemon is not running.
        """
        return service_running("slurmctld")

    @property
    def hash(self) -> str:
        """sha224 hash of `slurm.conf`.

        Raises:
            SlurmConfNotFoundError: Thrown if `/etc/slurm/slurm.conf` does not exist on unit.

        Returns:
            str: sha224 hash of `slurm.conf`.
        """
        if os.path.isfile("/etc/slurm/slurm.conf"):
            sha224 = hashlib.sha224()
            sha224.update(open("/etc/munge/munge.key", "rb").read())
            return sha224.hexdigest()
        else:
            raise SlurmConfNotFoundError("/etc/slurm/slurm.conf", self.__class__.__name__)

    @property
    def conf_file(self) -> str:
        """Location of slurm configuration file on unit.

        Raises:
            SlurmConfNotFoundError: Thrown if `/etc/slurm/slurm.conf` does not exist on unit.

        Returns:
            str: Path to slurm configuration file on unit.
        """
        if os.path.isfile("/etc/slurm/slurm.conf"):
            return "/etc/slurm/slurm.conf"
        else:
            raise SlurmConfNotFoundError("/etc/slurm/slurm.conf", self.__class__.__name__)

    def generate_new_conf(self) -> None:
        """Generate a base configuration file for slurm."""
        if os.path.isfile("/etc/slurm/slurm.conf"):
            os.remove("/etc/slurm/slurm.conf")
        open("/etc/slurm/slurm.conf", "w").close()
        editor = SlurmConfFileEditor()
        editor.load()
        content = [
            f"SlurmctldHost={self.__get_hostname()}({self.__get_ipv4_address()})",
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
        conf = [line.strip() for line in open("/etc/slurm/slurm.conf")]

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

        with open("/etc/slurm/slurm.conf", "wt") as fout:
            for line in conf:
                fout.write(f"{line}\n")

    def add_node(self, **kwargs) -> None:
        """Add a new node to the slurm configuration file."""
        nodename = kwargs.get("nodename", None)
        nodeaddr = kwargs.get("nodeaddr", None)
        cpus = kwargs.get("cpus", None)
        realmemory = kwargs.get("realmemory", None)
        self.__lint_node_conf(nodename, nodeaddr, cpus, realmemory)

        editor = SlurmConfFileEditor()
        editor.load()
        editor.add_line(
            f"NodeName={nodename} NodeAddr={nodeaddr} CPUs={cpus} RealMemory={realmemory}"
        )
        editor.dump()

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
        if self.__is_installed():
            logger.debug("Starting slurmctld service.")
            if not service_running("slurmctld"):
                service_start("slurmctld")
                logger.debug("slurmctld service started.")
            else:
                logger.debug("slurmctld service is already running.")
        else:
            raise SlurmctldNotFoundError(self.__class__.__name__)

    def stop(self) -> None:
        """Stop SLURM central management daemon."""
        if self.__is_installed():
            logger.debug("Stopping slurmctld service.")
            if service_running("slurmctld"):
                service_stop("slurmctld")
                logger.debug("slurmctld service stopped.")
            else:
                logger.debug("slurmctld service is already stopped.")
        else:
            raise SlurmctldNotFoundError(self.__class__.__name__)

    def restart(self) -> None:
        """Restart SLURM central management daemon."""
        if self.__is_installed():
            logger.debug("Restarting slurmctld service.")
            service_restart("slurmctld")
            logger.debug("slurmctld service restarted.")
        else:
            raise SlurmctldNotFoundError(self.__class__.__name__)

    def __is_installed(self) -> bool:
        """Internal function to check if slurmctld Debian package is installed on the unit.

        Returns:
            bool: True if Debian package is present; False if Debian package is not present.
        """
        try:
            slurmctld_status = apt.DebianPackage.from_installed_package("slurmctld")
            if slurmctld_status.present:
                return True
            else:
                return False
        except apt.PackageNotFoundError:
            return False

    def __get_hostname(self) -> str:
        """Internal function to retrieve hostname of unit.

        Returns:
            str: Hostname of unit.
        """
        return self.__network.info["hostname"]

    def __get_ipv4_address(self) -> ipaddress.IPv4Address:
        """Internal function to retrieve IPv4 address of unit's eth0 interface.

        Returns:
            ipaddress.IPv4Address: IPv4 address of unit's eth0 interface.
        """
        for iface in self.__network.info["ifaces"]:
            if iface["name"] == "eth0":
                for addr in iface["info"]["addr_info"]:
                    if addr["family"] == "inet":
                        return addr["address"]

    def __lint_node_conf(self, *args) -> None:
        """Internal function to lint received compute node configuration.

        Raises:
            InvalidNodeConfError: Thrown if configuration value is missing.
        """
        for arg in args:
            if arg is None:
                raise InvalidNodeConfError(arg)
