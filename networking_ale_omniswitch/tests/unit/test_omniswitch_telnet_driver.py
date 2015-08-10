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


import unittest

from networking_ale_omniswitch import omniswitch_constants as omni_const
from networking_ale_omniswitch.tests.unit.omniswitch_telnet_driver_test import OmniSwitchTelnetDriverTestClass


class OmniSwitchTelnetDriverUnitTestClass(unittest.TestCase):
    """Name:        OmniSwitchTelnetDriverUnitTestClass
    Description: OmniSwitchTelnetDriverUnitTestClass contains all unittest code for
                 OmniSwitchTelnetDriver(omniswitch_telnet_driver.py module)
    Details:     unittest and Mock are used for implementing unittest for OmniSwitchTelnetDriverUnitTestClass.
                 xmlrunner module is used to for generating test repport
                 To run all test cases in this file, type 'python test_omniswitch_telnet_driver.py'
    """

    def setUp(self):
        super(OmniSwitchTelnetDriverUnitTestClass, self).setUp()
        self.telnet_driver = OmniSwitchTelnetDriverTestClass('127.0.0.1', omni_const.OMNISWITCH_6XX,
                                                             'admin', 'switch', '->')
        self.telnet_driver.clean_commands()

    def __assert_equal(self, expected_commands):
        actual_commands = self.telnet_driver.get_commands()
        self.assertEqual(actual_commands, expected_commands)

    def test_create_vpa(self):
        # OMNISWITCH_6XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_6XX)

        # Case 1: vlan_id = 1; slotport = 2
        vlan_id = '1'
        slotport = '2'
        self.telnet_driver.clean_commands()
        self.telnet_driver.create_vpa(vlan_id, slotport)
        self.__assert_equal(['vlan 1 802.1q 2'])

        # case 2: vlan_id = 1; slotport = '1/2'
        vlan_id = '1'
        slotport = '1/2'
        self.telnet_driver.clean_commands()
        self.telnet_driver.create_vpa(vlan_id, slotport)
        self.__assert_equal(['vlan 1 802.1q 1/2'])

        # OMNISWITCH_7XX and OMNISWITCH_8XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_7XX)

        # Case 1: vlan_id = 1; slotport = 2
        vlan_id = '1'
        slotport = '2'
        self.telnet_driver.clean_commands()
        self.telnet_driver.create_vpa(vlan_id, slotport)
        self.__assert_equal(['vlan 1 members linkagg 2 tagged'])

        # case 2: vlan_id = 1; slotport = '1/2'
        self.telnet_driver.clean_commands()
        vlan_id = '1'
        slotport = '1/2'
        self.telnet_driver.create_vpa(vlan_id, slotport)
        self.__assert_equal(['vlan 1 members port 1/2 tagged'])

    def test_delete_vpa(self):
        # OMNISWITCH_6XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_6XX)

        # Case 1: vlan_id = 1; slotport = 2
        vlan_id = '1'
        slotport = '2'
        self.telnet_driver.clean_commands()
        self.telnet_driver.delete_vpa(vlan_id, slotport)
        self.__assert_equal(['no 802.1q 2'])

        # case 2: vlan_id = 1; slotport = '1/2'
        vlan_id = '1'
        slotport = '1/2'
        self.telnet_driver.clean_commands()
        self.telnet_driver.delete_vpa(vlan_id, slotport)
        self.__assert_equal(['no 802.1q 1/2'])

        # OMNISWITCH_7XX and OMNISWITCH_8XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_8XX)

        # Case 1: vlan_id = 1; slotport = 2
        vlan_id = '1'
        slotport = '2'
        self.telnet_driver.clean_commands()
        self.telnet_driver.delete_vpa(vlan_id, slotport)
        self.__assert_equal(['no vlan 1 members linkagg 2'])

        # case 2: vlan_id = 1; slotport = '1/2'
        vlan_id = '1'
        slotport = '1/2'
        self.telnet_driver.clean_commands()
        self.telnet_driver.delete_vpa(vlan_id, slotport)
        self.__assert_equal(['no vlan 1 members port 1/2'])

    def test_create_vlan(self):
        vlan_id = '1'
        net_name = 'OpenStack'
        self.telnet_driver.clean_commands()
        self.telnet_driver.create_vlan(vlan_id, net_name)
        self.__assert_equal(['vlan 1 name OpenStack'])

    def test_update_vlan(self):
        # test_create_vlan
        # update_vlan method delegates its work to create_vlan method. no need to test twice
        self.skipTest('update_vlan method delegates its work to create_vlan method. no need to test twice')

    def test_delete_vlan(self):
        vlan_id = '1'
        self.telnet_driver.delete_vlan(vlan_id)
        self.__assert_equal(['no vlan 1'])

    def test_create_network(self):
        # omni_const.OMNISWITCH_8XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_8XX)

        vlan_id = 1
        net_name = 'OpenStack'

        self.telnet_driver.clean_commands()
        self.telnet_driver.create_network(vlan_id, net_name)
        self.__assert_equal(['vlan 1 name OpenStack'])

    def test_update_network(self):
        # test_create_vlan
        # update_network method delegates its work to create_vlan method. no need to test twice
        self.skipTest('update_network method delegates its work to create_vlan method. no need to test twice')

    def test_delete_network(self):
        # omni_const.OMNISWITCH_8XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_8XX)

        vlan_id = 1
        self.telnet_driver.clean_commands()
        self.telnet_driver.delete_network(vlan_id)
        self.__assert_equal(['no vlan 1'])

    def test_enable_stp_mode_flat(self):
        # OMNISWITCH_6XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_6XX)

        self.telnet_driver.clean_commands()
        self.telnet_driver.enable_stp_mode_flat()
        self.__assert_equal(['bridge mode flat'])

        # OMNISWITCH_7XX and 8XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_8XX)

        self.telnet_driver.clean_commands()
        self.telnet_driver.enable_stp_mode_flat()
        self.__assert_equal(['spantree mode flat'])

    def test_disable_stp_mode_flat(self):
        # OMNISWITCH_6XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_6XX)

        self.telnet_driver.clean_commands()
        self.telnet_driver.disable_stp_mode_flat()
        self.__assert_equal(['bridge mode 1x1'])

        # OMNISWITCH_7XX and 8XX#
        self.telnet_driver.set_switch_type(omni_const.OMNISWITCH_8XX)

        self.telnet_driver.clean_commands()
        self.telnet_driver.disable_stp_mode_flat()
        self.__assert_equal(['spantree mode per-vlan'])

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(OmniSwitchTelnetDriverUnitTestClass)
    test_result = unittest.TextTestRunner(verbosity=0).run(suite)
    print "All tests: ", test_result.testsRun
    print "Error(s): ", len(test_result.errors)
    print "Failure(s): ", len(test_result.failures)
    print "Skip(s): ", len(test_result.skipped)
