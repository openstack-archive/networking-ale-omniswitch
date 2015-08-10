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


import mock
import unittest

from mock import MagicMock
from oslo_config import cfg

from networking_ale_omniswitch import config  # noqa
from networking_ale_omniswitch import omniswitch_constants as omni_const
from networking_ale_omniswitch.tests.unit.omniswitch_restful_driver_test import OmniSwitchRestfulDriverTestClass
from networking_ale_omniswitch.tests.unit.omniswitch_telnet_driver_test import OmniSwitchTelnetDriverTestClass

device_opts = {
    'omni_edge_devices': ['10.255.222.20:OS10K:admin:switch:->:REST:1/20 1/21:1/22',
                          '10.255.222.21:OS10K:admin:switch:->:TELNET:1/20 1/21:1/22'],
    'omni_core_devices': ['10.255.222.30:OS10K:admin:switch:->:TELNET:1/1 1/2'],
    'dhcp_server_interface': '10.255.222.31:OS10K:admin:switch:->:TELNET:1/1'
}

for opt, val in device_opts.items():
    cfg.CONF.set_override(opt, val, 'ml2_ale_omniswitch')

from networking_ale_omniswitch.omniswitch_device_plugin import OmniSwitchDevicePluginV2


time_mock = MagicMock()
time_mock.sleep.return_value = 0

modules = {
    'time': time_mock,
}

module_patcher = mock.patch.dict('sys.modules', modules)
module_patcher.start()

EDGE_10K_REST_IP = '10.255.222.20'
EDGE_10K_TELNET_IP = '10.255.222.21'
CORE_10K_TELNET_IP = '10.255.222.30'


class FakeContext(object):
    def __init__(self):
        pass


def load_edge_stub_ddi(self):
    if len(self.core_device_list) == 0:
        return
    self.edge_ddi_list = dict()

    for device in self.edge_device_list:
        drv_type = self._get_driver_type(device[omni_const.OMNI_CFG_DEV_TYPE])

        if self.omniswitch_6xx(device):
            self.edge_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                          OmniSwitchTelnetDriverTestClass(
                                              device[omni_const.OMNI_CFG_DEV_IP],
                                              drv_type,
                                              device[omni_const.OMNI_CFG_DEV_PROMPT]))
            # for both 7XX and 8XX
        elif self.switch_access_rest(device):
            self.edge_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                          OmniSwitchRestfulDriverTestClass(
                                              device[omni_const.OMNI_CFG_DEV_IP],
                                              drv_type,
                                              device[omni_const.OMNI_CFG_DEV_LOGIN],
                                              device[omni_const.OMNI_CFG_DEV_PASSWORD]))
        else:
            self.edge_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                          OmniSwitchTelnetDriverTestClass(
                                              device[omni_const.OMNI_CFG_DEV_IP],
                                              drv_type,
                                              device[omni_const.OMNI_CFG_DEV_LOGIN],
                                              device[omni_const.OMNI_CFG_DEV_PASSWORD]))


def load_core_stub_ddi(self):
    if len(self.core_device_list) == 0:
        return

    self.core_ddi_list = dict()

    for device in self.core_device_list:
        drv_type = self._get_driver_type(device[omni_const.OMNI_CFG_DEV_TYPE])

        if self.omniswitch_6xx(device):
            self.core_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                          OmniSwitchTelnetDriverTestClass(
                                              device[omni_const.OMNI_CFG_DEV_IP],
                                              drv_type,
                                              device[omni_const.OMNI_CFG_DEV_PROMPT]))
            # for both 7XX and 8XX
        elif self.switch_access_rest(device):
            self.core_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                          OmniSwitchRestfulDriverTestClass(
                                              device[omni_const.OMNI_CFG_DEV_IP],
                                              drv_type,
                                              device[omni_const.OMNI_CFG_DEV_LOGIN],
                                              device[omni_const.OMNI_CFG_DEV_PASSWORD]))
        else:
            self.core_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                          OmniSwitchTelnetDriverTestClass(
                                              device[omni_const.OMNI_CFG_DEV_IP],
                                              drv_type,
                                              device[omni_const.OMNI_CFG_DEV_LOGIN],
                                              device[omni_const.OMNI_CFG_DEV_PASSWORD]))


def load_dhcp_if_stub_inst(self):
    if self.dhcp_service is None:
        return

    self.dhcp_if_inst = None

    drv_type = self._get_driver_type(self.dhcp_service[omni_const.OMNI_CFG_DEV_TYPE])
    if self.omniswitch_6xx(self.dhcp_service):
        self.dhcp_if_inst = OmniSwitchTelnetDriverTestClass(
            self.dhcp_service[omni_const.OMNI_CFG_DEV_IP],
            drv_type,
            self.dhcp_service[omni_const.OMNI_CFG_DEV_LOGIN],
            self.dhcp_service[omni_const.OMNI_CFG_DEV_PASSWORD],
            self.dhcp_service[omni_const.OMNI_CFG_DEV_PROMPT]
            )
    else:  # for both 7XX and 8XX
        if self.device_access_rest(self.dhcp_service):
            self.dhcp_if_inst = OmniSwitchRestfulDriverTestClass(
                self.dhcp_service[omni_const.OMNI_CFG_DEV_IP],
                drv_type,
                self.dhcp_service[omni_const.OMNI_CFG_DEV_LOGIN],
                self.dhcp_service[omni_const.OMNI_CFG_DEV_PASSWORD]
                )
        else:
            self.dhcp_if_inst = OmniSwitchTelnetDriverTestClass(
                self.dhcp_service[omni_const.OMNI_CFG_DEV_IP],
                drv_type,
                self.dhcp_service[omni_const.OMNI_CFG_DEV_LOGIN],
                self.dhcp_service[omni_const.OMNI_CFG_DEV_PASSWORD])


class OmniSwitchDevicePluginV2UnitTestClass(unittest.TestCase):
    """Name:           OmniSwitchDevicePluginV2UnitTestClass
    Description:    OmniSwitchDevicePluginV2UnitTestClass contains all unittest code for OmniSwitchDevicePluginV2
                    (omniswitch_device_plugin.py module)
    Details:        unittest and Mock are used for implementing unittest for OmniSwitchDevicePluginV2.
                    Type 'python test_omniswitch_device_plugin.py' to run the test
    """

    def setUp(self):
        super(OmniSwitchDevicePluginV2UnitTestClass, self).setUp()
        self.do_mock()

        self.list_ddi = {}
        self.list_ddi.update(self.device_object.edge_ddi_list)
        self.list_ddi.update(self.device_object.core_ddi_list)
        # self.clean_ddi_commands()

    def do_mock(self):
        self.mock_start_thread = mock.patch.object(
            OmniSwitchDevicePluginV2,
            '_start_save_config_thread', new=mock_start_save_config_thread).start()

        self.device_object = OmniSwitchDevicePluginV2()

        self.mock_save_edge_config = mock.patch.object(
            self.device_object,
            'save_edge_config', new=mock_save_edge_config)
        self.mock_save_edge_config.start()

        self.mock_save_core_config = mock.patch.object(
            self.device_object,
            'save_core_config', new=mock_save_core_config)
        self.mock_save_core_config.start()

        self.load_stub_ddi()

    def load_stub_ddi(self):
        load_edge_stub_ddi(self.device_object)
        load_core_stub_ddi(self.device_object)
        load_dhcp_if_stub_inst(self.device_object)

    def tearDown(self):
        mock.patch.stopall()
        super(OmniSwitchDevicePluginV2UnitTestClass, self).tearDown()

    def get_dhcp_driver(self):
        return self.device_object.dhcp_if_inst

    def get_dhcp_driver_executed_commands(self):
        dhcp_driver = self.get_dhcp_driver()
        if isinstance(dhcp_driver, OmniSwitchRestfulDriverTestClass):
            return dhcp_driver.get_objects()
        elif isinstance(dhcp_driver, OmniSwitchTelnetDriverTestClass):
            return dhcp_driver.get_commands()
        else:
            return []

    def get_device_ddi(self, ip):
        return self.list_ddi[ip]

    def get_ddi_executed_commands(self, ddi):
        if isinstance(ddi, OmniSwitchRestfulDriverTestClass):
            return ddi.get_objects()
        elif isinstance(ddi, OmniSwitchTelnetDriverTestClass):
            return ddi.get_commands()
        else:
            return []

    def clean_ddi_commands(self):
        for ip in self.list_ddi:
            if isinstance(self.list_ddi[ip], OmniSwitchRestfulDriverTestClass):
                self.list_ddi[ip].clean_objects()
            elif isinstance(self.list_ddi[ip], OmniSwitchTelnetDriverTestClass):
                self.list_ddi[ip].clean_commands()

    def get_device_executed_commands(self, ip):
        return self.get_ddi_executed_commands(self.get_device_ddi(ip))

    def test_config_vpa_core(self):
        # Case 1: OMNI_CFG_CREATE
        net_name = "Openstack"
        self.clean_ddi_commands()
        self.device_object._config_vpa_core(1, omni_const.OMNI_CFG_CREATE, net_name)

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [
            'vlan 1 members port 1/22 tagged'
        ])

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [
            {'mibObject1': 'vpaVlanNumber:1', 'mibObject0': 'vpaIfIndex:1022', 'mibObject2': 'vpaType:2'}
        ])

        self.assertEqual(self.get_device_executed_commands(CORE_10K_TELNET_IP), [
            'vlan 1 name Openstack',
            'vlan 1 members port 1/1 tagged',
            'vlan 1 members port 1/2 tagged'
        ])

        # Case 2: OMNI_CFG_UPDATE
        self.clean_ddi_commands()
        self.device_object._config_vpa_core(1, omni_const.OMNI_CFG_UPDATE, net_name)

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [])

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [])

        self.assertEqual(self.get_device_executed_commands(CORE_10K_TELNET_IP), [
            'vlan 1 name Openstack'
        ])

        # Case 3: OMNI_CFG_DELETE
        self.clean_ddi_commands()
        self.device_object._config_vpa_core(1, omni_const.OMNI_CFG_DELETE, net_name)

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [])

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [])

        self.assertEqual(self.get_device_executed_commands(CORE_10K_TELNET_IP), [
            'no vlan 1'
        ])

    def test_config_vpa_edge(self):
        # Case 1: OMNI_CFG_CREATE
        self.clean_ddi_commands()
        self.device_object._config_vpa_edge(self.get_device_ddi(EDGE_10K_REST_IP), 1, omni_const.OMNI_CFG_CREATE)
        self.device_object._config_vpa_edge(self.get_device_ddi(EDGE_10K_TELNET_IP), 1, omni_const.OMNI_CFG_CREATE)

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [
            {'mibObject1': 'vpaVlanNumber:1', 'mibObject0': 'vpaIfIndex:1020', 'mibObject2': 'vpaType:2'},
            {'mibObject1': 'vpaVlanNumber:1', 'mibObject0': 'vpaIfIndex:1021', 'mibObject2': 'vpaType:2'}
        ])
        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [
            'vlan 1 members port 1/20 tagged',
            'vlan 1 members port 1/21 tagged'
        ])

        # Case 2: OMNI_CFG_DELETE
        self.clean_ddi_commands()
        self.device_object._config_vpa_edge(self.get_device_ddi(EDGE_10K_REST_IP), 1, omni_const.OMNI_CFG_DELETE)
        self.device_object._config_vpa_edge(self.get_device_ddi(EDGE_10K_TELNET_IP), 1, omni_const.OMNI_CFG_DELETE)

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [
            {'mibObject1': 'vpaVlanNumber:1', 'mibObject0': 'vpaIfIndex:1020'},
            {'mibObject1': 'vpaVlanNumber:1', 'mibObject0': 'vpaIfIndex:1021'}]
        )
        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [
            'no vlan 1 members port 1/20',
            'no vlan 1 members port 1/21'
        ])

    def test_save_core_config(self):
        self.mock_save_core_config.stop()
        self.clean_ddi_commands()
        self.device_object.save_core_config(1)
        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [])
        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [])
        self.assertEqual(self.get_device_executed_commands(CORE_10K_TELNET_IP), [
            'write memory flash-synchro'
        ])

    def test_save_edge_config(self):
        self.mock_save_edge_config.stop()
        self.clean_ddi_commands()
        self.device_object.save_edge_config(1)

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [
            {'mibObject0': 'configWriteMemory:1'},
            {'mibObject1': 'chasControlVersionMngt:2', 'mibObject0': 'entPhysicalIndex:65'}
        ])
        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [
            'write memory flash-synchro'
        ])
        self.assertEqual(self.get_device_executed_commands(CORE_10K_TELNET_IP), [])

    @mock.patch.object(OmniSwitchDevicePluginV2, 'cn_dhcp_config')
    @mock.patch.object(OmniSwitchDevicePluginV2, 'cn_core_config')
    @mock.patch.object(OmniSwitchDevicePluginV2, 'cn_edge_config')
    def test_create_network(self, m_cn_edge_config, m_cn_core_config, m_cn_dhcp_config):
        m_cn_edge_config.return_value = True
        m_cn_core_config.return_value = True

        mech_context = FakeContext()
        mech_context.current = {'name': 'test_network'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.create_network(mech_context)
        m_cn_edge_config.assert_called_with(mech_context)
        m_cn_core_config.assert_called_with(mech_context)
        m_cn_dhcp_config.assert_called_with(mech_context)

    @mock.patch.object(OmniSwitchDevicePluginV2, 'un_core_config')
    @mock.patch.object(OmniSwitchDevicePluginV2, 'un_edge_config')
    def test_update_network(self, m_un_edge_config, m_un_core_config):

        mech_context = FakeContext()
        mech_context.current = {'name': 'test_network'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.update_network(mech_context)
        m_un_edge_config.assert_called_with(mech_context)
        m_un_core_config.assert_called_with(mech_context)

    @mock.patch.object(OmniSwitchDevicePluginV2, 'dn_edge_config')
    @mock.patch.object(OmniSwitchDevicePluginV2, 'dn_core_config')
    @mock.patch.object(OmniSwitchDevicePluginV2, 'dn_dhcp_config')
    def test_delete_network(self, m_dn_dhcp_config, m_dn_core_config, m_dn_edge_config):
        mech_context = FakeContext()
        mech_context.current = {'name': 'test_network'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.delete_network(mech_context)

        m_dn_dhcp_config.assert_called_with(mech_context)
        m_dn_core_config.assert_called_with(mech_context)
        m_dn_edge_config.assert_called_with(mech_context)

    def test_cn_edge_config(self):
        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.cn_edge_config(mech_context)
        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [
            {'mibObject1': 'vlanDescription:Openstack', 'mibObject0': 'vlanNumber:100'},
            {'mibObject1': 'vpaVlanNumber:100', 'mibObject0': 'vpaIfIndex:1020', 'mibObject2': 'vpaType:2'},
            {'mibObject1': 'vpaVlanNumber:100', 'mibObject0': 'vpaIfIndex:1021', 'mibObject2': 'vpaType:2'}
        ])

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [
            'vlan 100 name Openstack',
            'vlan 100 members port 1/20 tagged',
            'vlan 100 members port 1/21 tagged'
        ])

    @mock.patch.object(OmniSwitchDevicePluginV2, 'delete_network')
    @mock.patch.object(OmniSwitchDevicePluginV2, '_config_vpa_core')
    def test_cn_core_config(self, m_config_vpa_core, m_delete_network):
        m_config_vpa_core.return_value = False

        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.device_object.cn_core_config(mech_context)
        m_config_vpa_core.assert_called_with(100, omni_const.OMNI_CFG_CREATE, 'Openstack')
        m_delete_network.assert_called_with(mech_context)

    def test_cn_dhcp_config(self):
        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.cn_dhcp_config(mech_context)

        self.assertEqual(self.get_dhcp_driver_executed_commands(), [
            'vlan 100 members port 1/1 tagged'
        ])

    def test_un_edge_config(self):
        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.un_edge_config(mech_context)

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [
            {'mibObject1': 'vlanDescription:Openstack', 'mibObject0': 'vlanNumber:100'}
        ])
        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [
            'vlan 100 name Openstack'
        ])
        self.assertEqual(self.get_device_executed_commands(CORE_10K_TELNET_IP), [])

    @mock.patch.object(OmniSwitchDevicePluginV2, '_config_vpa_core')
    def test_un_core_config(self, m_config_vpa_core):
        m_config_vpa_core.return_value = True
        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.un_core_config(mech_context)
        m_config_vpa_core.assert_called_with(100, omni_const.OMNI_CFG_UPDATE, 'Openstack')

    def test_un_dhcp_config(self):
        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.un_dhcp_config(mech_context)
        self.assertEqual(self.get_dhcp_driver_executed_commands(), [
            'vlan 100 name Openstack'
        ])

    def test_dn_edge_config(self):
        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.dn_edge_config(mech_context)

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_REST_IP), [
            {'mibObject1': 'vpaVlanNumber:100', 'mibObject0': 'vpaIfIndex:1020'},
            {'mibObject1': 'vpaVlanNumber:100', 'mibObject0': 'vpaIfIndex:1021'},
            {'mibObject0': 'vlanNumber:100'}
        ])

        self.assertEqual(self.get_device_executed_commands(EDGE_10K_TELNET_IP), [
            'no vlan 100 members port 1/20',
            'no vlan 100 members port 1/21',
            'no vlan 100'
        ])

        self.assertEqual(self.get_device_executed_commands(CORE_10K_TELNET_IP), [])

    @mock.patch.object(OmniSwitchDevicePluginV2, '_config_vpa_core')
    def test_dn_core_config(self, m_config_vpa_core):
        m_config_vpa_core.return_value = False

        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})

        self.clean_ddi_commands()
        self.device_object.dn_core_config(mech_context)
        m_config_vpa_core.assert_called_with(100, omni_const.OMNI_CFG_DELETE)

    def test_dn_dhcp_config(self):
        self.clean_ddi_commands()
        mech_context = FakeContext()
        mech_context.current = {'name': 'Openstack'}
        mech_context.network_segments = []
        mech_context.network_segments.append({'segmentation_id': 100})
        self.device_object.dn_dhcp_config(mech_context)
        self.assertEqual(self.get_dhcp_driver_executed_commands(), [
            'no vlan 100 members port 1/1'
        ])


def mock_save_edge_config(*args):
    pass


def mock_save_core_config(*args):
    pass


def mock_start_save_config_thread(*args):
    pass

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(OmniSwitchDevicePluginV2UnitTestClass)
    test_result = unittest.TextTestRunner(verbosity=0).run(suite)
    print "All tests: ", test_result.testsRun
    print "Error(s): ", len(test_result.errors)
    print "Failure(s): ", len(test_result.failures)
    print "Skip(s): ", len(test_result.skipped)
