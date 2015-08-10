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

import logging
import threading
import time
import urllib2

from networking_ale_omniswitch.consumer import AOSAPI
from networking_ale_omniswitch.consumer import AOSConnection

LOG = logging.getLogger(__name__)


class OmniSwitchRestfulDriver(object):

    """Name:        OmniSwitchRestfulDriver.
    Description: OmniSwitch device driver to communicate with OS6900 and OS10K devices which support
                 RESTful interface.
    Details:     It is used by OmniSwitchDevicePluginV2 to perform the necessary configuration on the physical
                 switches as response to OpenStack networking APIs. This driver is used only for OS6900, OS10K
                 and OS6860 devices which support RESTful APIs to configure them. This driver requires the following
                 minimum version of AOS SW to be running on these devices...
                        OS10K  : 732-R01-GA
                        OS6900 : 733-R01-GA
                        OS6860 : 811-R01-GA
                 It uses the "consumer.py" library provided as a reference implementation from the AOS/OmniSwitch
                 point of view. No changes is made as part of OmniSwitch plug-in or driver development. For
                 latest version of consumer.py, refer "//depot/7.3.3.R01/sw/management/web/consumer/consumer.py".
                 For any issues/bugs with the library, please contact AOS 7x WebService module owner
                 (Chris Ravanscoft).
    """
    def __init__(self, ip, platform, login='admin', password='switch', prompt='->'):
        self.switch_type = platform
        self.switch_ip = ip.strip()
        if len(self.switch_ip) == 0:
            LOG.info("Init Error! Must provide a valid IP address!!!")
            return

        self.switch_login = login.strip()
        if len(self.switch_login) == 0:
            self.switch_login = 'admin'

        self.switch_password = password.strip()
        if len(self.switch_password) == 0:
            self.switch_password = 'switch'

        self.switch_prompt = prompt.strip()
        if len(self.switch_prompt) == 0:
            self.switch_prompt = '->'

        self.aosapi = AOSAPI(AOSConnection(
            self.switch_login,
            self.switch_password,
            self.switch_ip,
            True,
            True,
            True,
            -1,
            None,
            0,
            False))

        self.threadLock = threading.Lock()
        self._init_done = True

    def get_switch_type(self):
        return self.switch_type

    def get_ip(self):
        return self.switch_ip

    def connect(self):
        if not self._init_done:
            LOG.info("Driver is not initialized!!!")
            return False
        try:
            results = self.aosapi.login()
            if not self.aosapi.success():
                LOG.info("Login error %s: %s", self.switch_ip, results)
                return False
            else:
                return True
        except urllib2.HTTPError, e:
            self.aosapi.logout()
            LOG.info("Connect Error %s: %s", self.switch_ip, e)
            return False

    def disconnect(self):
        self.aosapi.logout()

    def create_vpa(self, vlan_id, slotport):
        self.threadLock.acquire(1)
        if not self.connect():
            self.threadLock.release()
            return False

        ifindex = self._get_ifindex_from_slotport(slotport)
        table = 'vpaTable'
        objs = {'mibObject0': 'vpaIfIndex:' + str(ifindex), 'mibObject1': 'vpaVlanNumber:' + str(vlan_id),
                'mibObject2': 'vpaType:2'}
        desc = "(create tagged vpa %s to %s) in %s" % (slotport, vlan_id, self.switch_ip)
        results = self.aosapi.put('mib', table, objs)['result']
        ret = self._log_results('put', 'mib', table, objs, desc, self.aosapi.success(), results)

        self.disconnect()
        self.threadLock.release()
        return ret

    def delete_vpa(self, vlan_id, slotport):
        self.threadLock.acquire(1)
        if not self.connect():
            self.threadLock.release()
            return False

        ifindex = self._get_ifindex_from_slotport(slotport)
        table = 'vpaTable'
        objs = {'mibObject0': 'vpaIfIndex:' + str(ifindex), 'mibObject1': 'vpaVlanNumber:' + str(vlan_id)}
        desc = "(delete vpa %s to %s) in %s" % (slotport, vlan_id, self.switch_ip)
        results = self.aosapi.delete('mib', table, objs)['result']
        ret = self._log_results('delete', 'mib', table, objs, desc, self.aosapi.success(), results)

        self.disconnect()
        self.threadLock.release()
        return ret

    def create_vlan_locked(self, vlan_id, net_name=''):
        self.threadLock.acquire(1)
        ret = self.create_vlan(vlan_id, net_name)
        self.threadLock.release()
        return ret

    def create_vlan(self, vlan_id, net_name=''):
        if not self.connect():
            return False
        domain = 'mib'
        table = 'vlanTable'
        objs = {'mibObject0': 'vlanNumber:' + str(vlan_id), 'mibObject1': 'vlanDescription:' + net_name}
        desc = "(create vlan %s name %s) in %s" % (vlan_id, net_name, self.switch_ip)
        results = self.aosapi.put(domain, table, objs)['result']
        ret = self._log_results('put', domain, table, objs, desc, self.aosapi.success(), results)
        self.disconnect()
        return ret

    def update_vlan_locked(self, vlan_id, net_name=''):
        self.threadLock.acquire(1)
        ret = self.update_vlan(vlan_id, net_name)
        self.threadLock.release()
        return ret

    def update_vlan(self, vlan_id, net_name=''):
        if not self.connect():
            return False

        domain = 'mib'
        table = 'vlanTable'
        objs = {'mibObject0': 'vlanNumber:' + str(vlan_id), 'mibObject1': 'vlanDescription:' + net_name}
        desc = "(update vlan %s name %s) in %s" % (vlan_id, net_name, self.switch_ip)
        results = self.aosapi.post(domain, table, objs)['result']
        ret = self._log_results('post', domain, table, objs, desc, self.aosapi.success(), results)
        self.disconnect()
        return ret

    def delete_vlan_locked(self, vlan_id):
        self.threadLock.acquire(1)
        ret = self.delete_vlan(vlan_id)
        self.threadLock.release()
        return ret

    def delete_vlan(self, vlan_id):
        if not self.connect():
            return False

        domain = 'mib'
        table = 'vlanTable'
        objs = {'mibObject0': 'vlanNumber:' + str(vlan_id)}
        desc = "(delete vlan %s) in %s" % (vlan_id, self.switch_ip)
        results = self.aosapi.delete(domain, table, objs)['result']
        ret = self._log_results('delete', domain, table, objs, desc, self.aosapi.success(), results)

        self.disconnect()
        return ret

    def write_memory(self):
        if not self.connect():
            return False

        domain = 'mib'
        table = 'configManager'
        objs = {'mibObject0': 'configWriteMemory:' + str(1)}
        desc = "(write memory) on %s" % self.switch_ip
        results = self.aosapi.post(domain, table, objs)['result']
        ret = self._log_results('post', domain, table, objs, desc, self.aosapi.success(), results)

        self.disconnect()
        return ret

    def copy_running_certified(self):
        if not self.connect():
            return False

        domain = 'mib'
        table = 'chasControlModuleTable'
        objs = {'mibObject0': 'entPhysicalIndex:' + str(65), 'mibObject1': 'chasControlVersionMngt:' + str(2)}
        desc = "(copy running certified) on %s" % self.switch_ip
        results = self.aosapi.post(domain, table, objs)['result']
        ret = self._log_results('post', domain, table, objs, desc, self.aosapi.success(), results, True, False)

        if not self.aosapi.success():
            table = 'chasControlModuleTable'
            objs = {'mibObject0': 'entPhysicalIndex:' + str(66), 'mibObject1': 'chasControlVersionMngt:' + str(2)}
            desc = "(copy running certified) on %s" % self.switch_ip
            results = self.aosapi.post(domain, table, objs)['result']
            ret = self._log_results('post', domain, table, objs, desc, self.aosapi.success(), results)

        self.disconnect()
        return ret

    def create_network(self, vlan_id, net_name=''):
        self.threadLock.acquire(1)
        ret = self.create_vlan(vlan_id, net_name)
        self.threadLock.release()
        return ret

    def update_network(self, vlan_id, net_name=''):
        self.threadLock.acquire(1)
        ret = self.update_vlan(vlan_id, net_name)
        self.threadLock.release()
        return ret

    def delete_network(self, vlan_id, ):
        self.threadLock.acquire(1)
        ret = self.delete_vlan(vlan_id)
        self.threadLock.release()
        return ret

    def enable_stp_mode_flat(self):
        if not self.connect():
            return False

        domain = 'mib'
        table = 'vStpBridge'
        objs = {'mibObject0': 'vStpBridgeMode:' + str(1)}
        desc = "(stp mode flat) in %s" % self.switch_ip
        results = self.aosapi.post(domain, table, objs)['result']
        ret = self._log_results('post', domain, table, objs, desc, self.aosapi.success(), results)

        self.disconnect()
        return ret

    def disable_stp_mode_flat(self):
        if not self.connect():
            return False

        domain = 'mib'
        table = 'vStpBridge'
        objs = {'mibObject0': 'vStpBridgeMode:' + str(2)}
        desc = "(stp mode 1X1) in %s" % self.switch_ip
        results = self.aosapi.post(domain, table, objs)['result']
        ret = self._log_results('post', domain, table, objs, desc, self.aosapi.success(), results)

        self.disconnect()
        return ret

    def save_config(self):
        self.threadLock.acquire(1)
        if self.write_memory():
            time.sleep(1)
            ret = self.copy_running_certified()
            time.sleep(2)
            self.threadLock.release()
            return ret
        else:
            ret = False
        self.threadLock.release()
        return ret

    def _get_ifindex_from_slotport(self, slotport):
        # convert slot/port = '1/2' to ifIndex = 1002
        # convert chassis/slot/port = '1/2/3' to ifIndex = 102003
        # convert linkagg id = '5' to ifIndex = 40000005

        if len(slotport.split('/')) == 3:
            chassis = int(slotport.split('/')[0])
            if chassis == 0:
                chassis = 1
            slot = int(slotport.split('/')[1])
            port = int(slotport.split('/')[2])
            return str(((chassis - 1) * 100000) + (slot * 1000) + port)
        elif len(slotport.split('/')) == 2:
            slot = int(slotport.split('/')[0])
            port = int(slotport.split('/')[1])
            return str((slot * 1000) + port)
        elif len(slotport.split('/')) == 1:
            linkagg = int(slotport.split('/')[0])
            return str(40000000 + linkagg)
        else:
            LOG.info("Error: ifIndex calc: invalid slotport %s", slotport)
            return 0

    def _log_results(self, cmd_type, domain, urn, args, cmd_desc, was_successful,
                     results, log_success=True, log_failure=True):
        objs_str = ', '.join(args.values())  # str(args) if cmd_type == 'query' else ', '.join(args.values())
        cmd_str = "sendCommand: %s <domain:%s; urn:%s; args:{ %s }> %s" % (cmd_type, domain, urn, objs_str, cmd_desc)
        if was_successful:
            if log_success:
                # print "%s was successful!" %(cmd_str)
                LOG.info("%s was successful!", cmd_str)
            return True
        else:
            if log_failure:
                # print "%s failed! %s" %(cmd_str, ', '.join(results['error'].values()))
                LOG.info("%s failed! %s", cmd_str, ', '.join(results['error'].values()))
            return False
