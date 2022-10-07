#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""HPC Team SLURM server charm."""

import logging
import secrets

from hpctinterfaces import interface_registry
from hpctops.charm.service import ServiceCharm
from hpctops.misc import service_forced_update
from ops.charm import (
    InstallEvent,
    RelationChangedEvent,
    RelationJoinedEvent,
    StartEvent,
    StopEvent,
)
from ops.main import main

import interfaces.auth_munge
import interfaces.slurm_compute
import interfaces.slurm_controller
from manager import MungeManager, SlurmServerManager

logger = logging.getLogger(__name__)


class SlurmServerCharm(ServiceCharm):
    """Slurm server charm. Encapsulates slurmctld and munge."""

    def __init__(self, *args) -> None:
        super().__init__(*args)

        self.slurm_server_manager = SlurmServerManager()
        self.munge_manager = MungeManager()

        self.auth_munge_siface = interface_registry.load("relation-auth-munge", self, "auth-munge")
        self.slurm_compute_siface = interface_registry.load(
            "relation-slurm-compute", self, "slurm-compute"
        )
        self.slurm_controller_siface = interface_registry.load(
            "relation-slurm-controller", self, "slurm-controller"
        )

        self.framework.observe(
            self.on.auth_munge_relation_joined, self._auth_munge_relation_joined
        )
        self.framework.observe(
            self.on.slurm_compute_relation_changed, self._slurm_compute_relation_changed
        )
        self.framework.observe(
            self.on.slurm_controller_relation_joined, self._slurm_controller_relation_joined
        )

    @service_forced_update()
    def _service_install(self, event: InstallEvent) -> None:
        """Fired when charm is first deployed."""
        self.service_set_status_message("Installing munge")
        self.service_update_status()
        self.munge_manager.install()

        self.service_set_status_message("Installing slurmctld")
        self.service_update_status()
        self.slurm_server_manager.install()
        self.slurm_server_manager.generate_new_conf()

        self.service_set_status_message()
        self.service_update_status()

    @service_forced_update()
    def _service_start(self, event: StartEvent) -> None:
        """Fired when service-start is run."""
        self.service_set_status_message("Starting munge")
        self.service_update_status()
        self.munge_manager.start()

        self.service_set_status_message("Starting slurmctld")
        self.service_update_status()
        self.slurm_server_manager.start()

        self.service_set_status_message()
        self.service_update_status()

    @service_forced_update()
    def _service_stop(self, event: StopEvent, force: bool) -> None:
        """Fired when service-stop is run."""
        self.service_set_status_message("Stopping slurmctld")
        self.service_update_status()
        self.slurm_server_manager.stop()

        self.service_set_status_message("Stopping munge")
        self.service_update_status()
        self.munge_manager.stop()

        self.service_set_status_message("Slurm server is not active.")
        self.service_update_status()

    @service_forced_update()
    def _auth_munge_relation_joined(self, event: RelationJoinedEvent) -> None:
        if self.unit.is_leader():
            self.service_set_status_message("Authenticating new compute node")
            self.service_update_status()
            iface = self.auth_munge_siface.select(self.app)

            iface.nonce = self.__create_nonce()
            iface.munge_key.load(self.munge_manager.key_file_path, checksum=True)
            self.service_set_status_message("Copy of munge key sent")
            self.service_update_status()

    @service_forced_update()
    def _slurm_compute_relation_changed(self, event: RelationChangedEvent) -> None:
        """Fired when compute node joins the cluster. Information is loaded from `event.unit`."""
        iface = self.slurm_compute_siface.select(event.unit)

        if iface.nonce == "":
            self.service_set_status_message("Compute node is not ready yet")
            self.service_update_status()
        elif self.unit.is_leader():
            self.service_set_status_message("Registering new compute node")
            self.service_update_status()
            self.slurm_server_manager.stop()
            self.slurm_server_manager.add_node(
                nodename=iface.hostname,
                nodeaddr=iface.ip_address,
                cpus=iface.cpu_count,
                realmemory=iface.free_memory,
            )
            self.slurm_server_manager.generate_base_partition()
            self.slurm_server_manager.start()

            out = self.slurm_controller_siface.select(self.app)
            out.slurm_conf.load(self.slurm_server_manager.conf_file_path, checksum=True)
        else:
            self.service_set_status_message("Leader registering new compute node")
            self.service_update_status()

    @service_forced_update()
    def _slurm_controller_relation_joined(self, event: RelationJoinedEvent) -> None:
        """Fired when new compute node is requesting slurm configuration."""
        self.service_set_status_message("New client detected")
        self.service_update_status()
        if self.unit.is_leader():
            self.service_set_status_message("Serving slurm configuration")
            self.service_update_status()
            iface = self.slurm_controller_siface.select(self.app)
            iface.nonce = self.__create_nonce()
            iface.slurm_conf.load(self.slurm_server_manager.conf_file_path, checksum=True)

    def __create_nonce(self) -> str:
        """Create a nonce.

        Returns:
            str: Created nonce.
        """
        return secrets.token_urlsafe()


if __name__ == "__main__":
    main(SlurmServerCharm)
