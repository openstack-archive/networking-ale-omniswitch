#  Copyright 2014 Alcatel-Lucent Enterprise.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file
#  except in compliance with the License. You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software distributed under the License
#  is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
#  either express or implied. See the License for the specific language governing permissions
#  and limitations under the License.


"""Implentation of Omniswitch ML2 Mechanism driver for ML2 Plugin."""


import logging

from neutron.plugins.ml2 import driver_api
from oslo_utils import importutils

from networking_ale_omniswitch import config  # noqa
from networking_ale_omniswitch import omniswitch_constants as omni_const

LOG = logging.getLogger(__name__)


class OmniswitchMechanismDriver(driver_api.MechanismDriver):

    def __init__(self):
        self.omni_plugin_obj = None
        super(OmniswitchMechanismDriver, self).__init__()

    def initialize(self):
        self.omniswitch_init()
        LOG.info("Device plug-ins loaded!")

    def omniswitch_init(self):
        self.omni_plugin_obj = importutils.import_object(omni_const.OMNI_DEVICE_PLUGIN)
        LOG.info("Device plug-ins loaded!")

    def create_network_precommit(self, mech_context):
        pass

    def create_network_postcommit(self, mech_context):
        LOG.debug("create_network_postcommit: called")
        network = mech_context.current
        segments = mech_context.network_segments
        segment = segments[0]  # currently supports only one segment per network
        network_type = segment['network_type']

        if network_type != 'vlan':
            raise Exception(
                "Omniswitch Mechanism: failed to create network, "
                "only network type vlan is supported")

        ret = self.omni_plugin_obj.create_network(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to create network in Omniswitches! %s", network)
            raise Exception(
                "Omniswitch Mechanism: failed to create network in Omniswitches! %s",
                network)

    def delete_network_precommit(self, mech_context):
        pass

    def delete_network_postcommit(self, mech_context):
        network = mech_context.current
        ret = self.omni_plugin_obj.delete_network(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to delete network in Omniswitches! %s", network)

    def update_network_precommit(self, mech_context):
        pass

    def update_network_postcommit(self, mech_context):
        network = mech_context.current

        ret = self.omni_plugin_obj.update_network(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to update network in Omniswitches! %s", network)
            raise Exception(
                "Omniswitch Mechanism: failed to update network in Omniswitches! %s",
                network)

    def create_port_precommit(self, mech_context):
        pass

    def create_port_postcommit(self, mech_context):
        port = mech_context.current
        ret = self.omni_plugin_obj.create_port(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to create port in Omniswitches! %s", port)
            raise Exception(
                "Omniswitch Mechanism: failed to create port in Omniswitches! %s", port)

    def delete_port_precommit(self, mech_context):
        pass

    def delete_port_postcommit(self, mech_context):
        port = mech_context.current

        ret = self.omni_plugin_obj.delete_port(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to delete port in Omniswitches! %s", port)

    def update_port_precommit(self, mech_context):
        pass

    def update_port_postcommit(self, mech_context):
        port = mech_context.current

        ret = self.omni_plugin_obj.update_port(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to delete port in Omniswitches! %s", port)
        pass

    def create_subnet_precommit(self, mech_context):
        pass

    def create_subnet_postcommit(self, mech_context):
        subnet = mech_context.current
        ret = self.omni_plugin_obj.create_subnet(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to delete subnet in Omniswitches! %s", subnet)
        pass

    def delete_subnet_precommit(self, mech_context):
        pass

    def delete_subnet_postcommit(self, mech_context):
        subnet = mech_context.current
        ret = self.omni_plugin_obj.delete_subnet(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to delete subnet in Omniswitches! %s", subnet)

    def update_subnet_precommit(self, mech_context):
        pass

    def update_subnet_postcommit(self, mech_context):
        subnet = mech_context.current
        ret = self.omni_plugin_obj.update_subnet(mech_context)
        if not ret:
            LOG.error("Omniswitch Mechanism: failed to delete subnet in Omniswitches! %s", subnet)
