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
import re
import telnetlib
import threading

from networking_ale_omniswitch import omniswitch_constants as omni_const


LOG = logging.getLogger(__name__)


class OmniSwitchTelnetDriver(object):

    """Name:        OmniSwitchTelnetDriver.
    Description: OmniSwitch device driver to communicate with AOS 6x devices such as OS6850E,
                 OS6855, OS6450 and OS6250 etc.
    Details:     It is used by OmniSwitchDevicePluginV2 to perform the necessary configuration on the physical
                 switches as response to OpenStack networking APIs. This driver is used only for above mentioned
                 AOS 6x devices.
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

        self.threadLock = threading.Lock()
        self._init_done = True
        self.telnetObj = None

    def get_switch_type(self):
        return self.switch_type

    def get_ip(self):
        return self.switch_ip

    def connect(self):
        if not self._init_done:
            LOG.info("Driver is not initialized!!!")
            return False

        self.telnetObj = telnetlib.Telnet(self.switch_ip, 23, 10)
        # self.telnetObj.set_debuglevel(10)

        self.telnetObj.read_until("login :", omni_const.OMNI_CLI_SMALL_TIMEOUT)
        self.telnetObj.write(self.switch_login + "\n")
        self.telnetObj.read_until("assword : ", omni_const.OMNI_CLI_SMALL_TIMEOUT)
        self.telnetObj.write(self.switch_password + "\n")
        if self.telnetObj.read_until(self.switch_prompt, omni_const.OMNI_CLI_PROMPT_TIMEOUT) is None:
            LOG.info("Connection to %s failed!", self.switch_ip)
            return False

        return True

    def disconnect(self):
        if self.telnetObj:
            self.telnetObj.close()
        self.telnetObj = None

    def is_connected(self):
        if self.telnetObj is None:
            return False

        self.telnetObj.write("\n\n")
        if self.telnetObj.read_until(self.switch_prompt, omni_const.OMNI_CLI_PROMPT_TIMEOUT) is None:
            return False
        else:
            return True

    def send_command(self, command):
        # LOG.info("sendCommand: <%s> to %s entry!", command, self.switch_ip)
        self.threadLock.acquire(1)
        # LOG.info("sendCommand: <%s> to %s lock acquired!", command, self.switch_ip)

        if not self.is_connected():
            if not self.connect():
                self.threadLock.release()
                # LOG.info("sendCommand: <%s> to %s lock released!", command, self.switch_ip)
                # LOG.info("sendCommand: <%s> to %s exit!", command, self.switch_ip)
                return False

        # if(self.isConnected() == True):
        if self.telnetObj:
            self.telnetObj.write(command)
            self.telnetObj.write("\n")
            ret = self.telnetObj.read_until("ERROR", 1)  # omni_const.OMNI_CLI_SMALL_TIMEOUT)
            # LOG.info("sendCommand: <%s> to %s, RETURNED = <%s>", command, self.switch_ip, ret)
            if re.search('ERROR', ret) is None:
                # this additional read makes command execute is completed
                self.telnetObj.read_until(self.switch_prompt, omni_const.OMNI_CLI_SMALL_TIMEOUT)
                LOG.info("sendCommand: <%s> to %s success!", command, self.switch_ip)
                self.threadLock.release()
                # LOG.info("sendCommand: <%s> to %s lock released!", command, self.switch_ip)
                # LOG.info("sendCommand: <%s> to %s exit!", command, self.switch_ip)
                return True
            else:
                ret = self.telnetObj.read_until('\n', omni_const.OMNI_CLI_SMALL_TIMEOUT)
                LOG.info("sendCommand: <%s> failed! in %s, ret = ERROR%s", command, self.switch_ip, ret)
                self.threadLock.release()
                # LOG.info("sendCommand: <%s> to %s lock released!", command, self.switch_ip)
                # LOG.info("sendCommand: <%s> to %s exit!", command, self.switch_ip)
                return False
        else:
            LOG.info("Could not connect to %s", self.switch_ip)
            LOG.info("sendCommand: <%s> failed!", command)
            self.threadLock.release()
            # LOG.info("sendCommand: <%s> to %s lock released!", command, self.switch_ip)
            # LOG.info("sendCommand: <%s> to %s exit!", command, self.switch_ip)
            return False

    def create_vpa(self, vlan_id, slotport):
        if self.switch_type == omni_const.OMNISWITCH_6XX:
            return self.send_command('vlan ' + str(vlan_id) + ' 802.1q ' + str(slotport))
        else:  # for both 7XX and 8XX
            if len(slotport.split('/')) == 1:
                ret = self.send_command('vlan ' + str(vlan_id) + ' members linkagg ' + str(slotport) + ' tagged')
            else:
                ret = self.send_command('vlan ' + str(vlan_id) + ' members port ' + str(slotport) + ' tagged')
        return ret

    def delete_vpa(self, vlan_id, slotport):
        if self.switch_type == omni_const.OMNISWITCH_6XX:
            return self.send_command('no 802.1q ' + str(slotport))
        else:  # for both 7XX and 8XX
            if len(slotport.split('/')) == 1:
                return self.send_command('no vlan ' + str(vlan_id) + ' members linkagg ' + str(slotport))
            else:
                return self.send_command('no vlan ' + str(vlan_id) + ' members port ' + str(slotport))

    def create_vlan_locked(self, vlan_id, net_name=''):
        return self.create_vlan(vlan_id, net_name)

    def create_vlan(self, vlan_id, net_name=''):
        return self.send_command(str('vlan ' + str(vlan_id) + ' name ' + net_name))

    def update_vlan_locked(self, vlan_id, net_name=''):
        return self.update_vlan(vlan_id, net_name)

    def update_vlan(self, vlan_id, net_name=''):
        return self.create_vlan(vlan_id, net_name)

    def delete_vlan_locked(self, vlan_id):
        return self.delete_vlan(vlan_id)

    def delete_vlan(self, vlan_id):
        return self.send_command('no vlan ' + str(vlan_id))

    def save_config(self):
        return self.write_memory_flash_synchro()

    def create_network(self, vlan_id, net_name=''):
        return self.create_vlan(vlan_id, net_name)

    def update_network(self, vlan_id, net_name=''):
        return self.update_vlan(vlan_id, net_name)

    def delete_network(self, vlan_id):
        return self.delete_vlan(vlan_id)

    def write_memory_flash_synchro(self):
        return self.send_command('write memory flash-synchro')

    def write_memory(self):
        return self.send_command('write memory')

    def copy_running_certified(self):
        if self.switch_type == omni_const.OMNISWITCH_6XX:
            return self.send_command('copy working certified')
        else:  # for both 7XX and 8XX
            return self.send_command('copy running certified')

    def create_vlan_vpa(self, vlan_id, net_name, slotport):
        if self.create_vlan(vlan_id, net_name):
            if self.create_vpa(vlan_id, slotport):
                return True
            else:
                self.delete_vlan(vlan_id)
                return False

    def enable_stp_mode_flat(self):
        if self.switch_type == omni_const.OMNISWITCH_6XX:
            return self.send_command('bridge mode flat')
        else:  # for both 7XX and 8XX
            return self.send_command('spantree mode flat')

    def disable_stp_mode_flat(self):
        if self.switch_type == omni_const.OMNISWITCH_6XX:
            return self.send_command('bridge mode 1x1')
        else:  # for both 7XX and 8XX
            return self.send_command('spantree mode per-vlan')
