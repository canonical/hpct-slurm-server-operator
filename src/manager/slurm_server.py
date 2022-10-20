#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Set up and manage slurmctld."""

import hashlib
import logging
import os
from typing import Union

from hpcteditors.app.slurm import SlurmConfFileEditor
from hpctmanagers import ManagerException
from hpctmanagers.ubuntu import UbuntuManager
from sysprober.network import Network

logger = logging.getLogger(__name__)


class SlurmServerManager(UbuntuManager):
    """Top-level manager class for controlling slurmctld on unit."""

    install_packages = ["slurmctld"]
    systemd_services = ["slurmctld"]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.__network = Network()
        self.conf_file_path = "/etc/slurm/slurm.conf"
        self.hostname = self.__network.info["hostname"]
        for iface in self.__network.info["ifaces"]:
            if iface["name"] == "eth0":
                for addr in iface["info"]["addr_info"]:
                    if addr["family"] == "inet":
                        self.ipv4_address = addr["address"]

    def get_hash(self, path: Union[str, None] = None) -> Union[str, None]:
        """Get the sha224 hash of a file.

        Args:
            path (str | None): Path to file to hash.
            Defaults to `self.conf_file_path` if path is None.

        Returns:
            str: sha224 hash of the file, or None if file does not exist.
        """
        path = self.conf_file_path if path is None else path
        return (
            hashlib.sha224(open(path, "rb").read()).hexdigest() if os.path.isfile(path) else None
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
        conf = [line.strip() for line in open(self.conf_file_path)]

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

        open(self.conf_file_path, "w").close()
        editor = SlurmConfFileEditor()
        editor.load()
        editor.add_lines(conf)
        editor.dump()

    def add_node(self, **kwargs) -> None:
        """Add a new node to the slurm configuration file.

        Raises:
            ManagerException: Thrown if a bad configuration is received from a node.
        """
        nodename = kwargs.get("nodename", None)
        nodeaddr = kwargs.get("nodeaddr", None)
        cpus = kwargs.get("cpus", None)
        realmemory = kwargs.get("realmemory", None)
        if None in [nodename, nodeaddr, cpus, realmemory]:
            raise ManagerException("Invalid node configuration received.")

        editor = SlurmConfFileEditor()
        editor.load()
        editor.add_line(
            f"NodeName={nodename} NodeAddr={nodeaddr} CPUs={cpus} RealMemory={realmemory}"
        )
        editor.dump()

    def restart(self) -> None:
        """Restart SLURM central management daemon.

        Raises:
            ManagerException: Thrown if slurmctld is not installed on unit.
        """
        if self.is_installed():
            logger.debug("Restarting slurmctld service.")
            self.stop()
            self.start()
            logger.debug("slurmctld service restarted.")
        else:
            raise ManagerException("slurmctld is not installed.")
