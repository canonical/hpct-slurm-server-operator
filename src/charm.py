#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""HPC Team SLURM server charm."""

import logging

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

from interface import (
    AuthMungeInterface,
    SlurmComputeInterface,
    SlurmControllerInterface,
)
from manager import MungeManager, SlurmServerManager

logger = logging.getLogger(__name__)


class SlurmServerCharm(ServiceCharm):
    """Slurm server charm. Encapsulates slurmctld and munge."""

    def __init__(self, *args) -> None:
        super().__init__(*args)

        self.slurm_server_manager = SlurmServerManager()
        self.munge_manager = MungeManager()

        self.auth_munge_interface = interface_registry.load(
            "relation-auth-munge", self, "auth-munge"
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
            i = self.auth_munge_interface.select(self.app)

            i.nonce = self.munge_manager.hash
            i.munge_key.load(self.munge_manager.key, checksum=True)
            self.service_set_status_message("Copy of munge key sent")
            self.service_update_status()

    @service_forced_update()
    def _slurm_compute_relation_changed(self, event: RelationChangedEvent) -> None:
        pass

    @service_forced_update()
    def _slurm_controller_relation_joined(self, event: RelationJoinedEvent) -> None:
        pass


if __name__ == "__main__":
    interface_registry.register("relation-auth-munge", AuthMungeInterface)
    interface_registry.register("relation-slurm-compute", SlurmComputeInterface)
    interface_registry.register("relation-slurm-controller", SlurmControllerInterface)
    main(SlurmServerCharm)
