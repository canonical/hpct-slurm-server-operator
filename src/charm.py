#!/usr/bin/env python3
# Copyright 2022 Canonical
# See LICENSE file for licensing details.

"""HPC Team SLURM server charm."""

import logging

from hpctlib.ops.charm.service import ServiceCharm
from ops.charm import ActionEvent, InstallEvent
from ops.framework import StoredState
from ops.main import main
from ops.model import ActiveStatus

from utils import SlurmManager


logger = logging.getLogger(__name__)


class SlurmServerCharm(ServiceCharm):

    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        self.manager = SlurmManager()

    def _service_install(self, event: InstallEvent) -> None:
        "Fired when charm is first deployed."
        self.manager.install("slurmctld")

    def _service_start(self, event: ActionEvent) -> None:
        "Fired when server-start action is invoked."
        pass
        

if __name__ == "__main__":
    main(SlurmServerCharm)
