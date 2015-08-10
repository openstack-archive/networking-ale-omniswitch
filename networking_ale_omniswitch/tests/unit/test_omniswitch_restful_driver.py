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
from networking_ale_omniswitch.tests.unit.omniswitch_restful_driver_test import OmniSwitchRestfulDriverTestClass


class OmniSwitchRestfulDriverUnitTestClass(unittest.TestCase):
    """Name:        OmniSwitchRestfulDriverUnitTestClass
    Description: OmniSwitchRestfulDriverUnitTestClass contains all unittest code for OmniSwitchRestfulDriver
                 (omniswitch_restful_driver.py module)
    Details:     unittest and Mock are used for implementing unittest for OmniSwitchRestfulDriverUnitTestClass.
                 xmlrunner module is used to for generating test repport
                 To run all test cases in this file, type 'python omniswitch_restful_driver.py'
    """

    def setUp(self):
        super(OmniSwitchRestfulDriverUnitTestClass, self).setUp()
        self.restful_driver = OmniSwitchRestfulDriverTestClass('127.0.0.1',
                                                               omni_const.OMNISWITCH_6XX, 'admin', 'switch', '->')

    def __assert_equal(self, expected_objects):
        actual_objects = self.restful_driver.get_objects()
        self.assertEqual(actual_objects, expected_objects)

    def test_create_vpa(self):
        # vlan_id = 1; slotport = 1/2
        vlan_id = 1
        slotport = '1/2'
        self.restful_driver.clean_objects()
        self.restful_driver.create_vpa(vlan_id, slotport)
        self.__assert_equal([{'mibObject0': 'vpaIfIndex:1002',
                              'mibObject1': 'vpaVlanNumber:1', 'mibObject2': 'vpaType:2'}])

    def test_delete_vpa(self):
        # vlan_id = 1; slotport = 1/2
        vlan_id = 1
        slotport = '1/2'
        self.restful_driver.clean_objects()
        self.restful_driver.delete_vpa(vlan_id, slotport)
        self.__assert_equal([{'mibObject0': 'vpaIfIndex:1002', 'mibObject1': 'vpaVlanNumber:1'}])

    def test_create_vlan(self):
        vlan_id = 1
        net_name = 'OpenStack'
        self.restful_driver.clean_objects()
        self.restful_driver.create_vlan(vlan_id, net_name)
        self.__assert_equal([{'mibObject0': 'vlanNumber:1', 'mibObject1': 'vlanDescription:OpenStack'}])

    def test_update_vlan(self):
        # test_create_vlan
        # update_vlan method delegates its work to create_vlan method. no need to test twice
        self.skipTest('update_vlan method delegates its work to create_vlan method. no need to test twice')

    def test_delete_vlan(self):
        vlan_id = 1
        self.restful_driver.clean_objects()
        self.restful_driver.delete_vlan(vlan_id)
        self.__assert_equal([{'mibObject0': 'vlanNumber:1'}])

    def test_enable_stp_mode_flat(self):
        self.restful_driver.clean_objects()
        self.restful_driver.enable_stp_mode_flat()
        self.__assert_equal([{'mibObject0': 'vStpBridgeMode:1'}])

    def test_disable_stp_mode_flat(self):
        self.restful_driver.clean_objects()
        self.restful_driver.disable_stp_mode_flat()
        self.__assert_equal([{'mibObject0': 'vStpBridgeMode:2'}])

    def test_create_network(self):
        # OMNISWITCH_8XX
        self.restful_driver.set_switch_type(omni_const.OMNISWITCH_8XX)
        vlan_id = 1
        net_name = 'OpenStack'
        self.restful_driver.clean_objects()
        self.restful_driver.create_network(vlan_id, net_name)
        self.__assert_equal([{'mibObject0': 'vlanNumber:1', 'mibObject1': 'vlanDescription:OpenStack'}])

    def test_update_network(self):
        # test_create_vlan
        # update_network method delegates its work to create_vlan method. no need to test twice
        self.skipTest('update_network method delegates its work to create_vlan method. no need to test twice')

    def test_delete_network(self):
        # OMNISWITCH_8XX
        self.restful_driver.set_switch_type(omni_const.OMNISWITCH_8XX)
        vlan_id = 1
        self.restful_driver.clean_objects()
        self.restful_driver.delete_network(vlan_id)
        self.__assert_equal([{'mibObject0': 'vlanNumber:1'}])

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(OmniSwitchRestfulDriverUnitTestClass)
    test_result = unittest.TextTestRunner(verbosity=0).run(suite)
    print "All tests: ", test_result.testsRun
    print "Error(s): ", len(test_result.errors)
    print "Failure(s): ", len(test_result.failures)
    print "Skip(s): ", len(test_result.skipped)
