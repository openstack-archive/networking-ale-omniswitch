#
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

from networking_ale_omniswitch.omniswitch_telnet_driver import OmniSwitchTelnetDriver

LOG = logging.getLogger(__name__)


class OmniSwitchTelnetDriverTestClass(OmniSwitchTelnetDriver):
    """Name:           OmniSwitchTelnetDriverTestClass
    Description:    OmniSwitchTelnetDriverTestClass only serves the purpose of implementing unittest for
                    OmniSwitchTelnetDriver (omniswitch_telnet_driver.py) module
    Details:        Since OmniSwitchTelnetDriver uses telnet lib to invoke shell command on real device,
                    we cannot directly add unittest for it.
                    The OmniSwitchTelnetDriverTestClass is created to stub the sendCommand operation of
                    OmniSwitchTelnetDriver and store commands to local self.commands member variable
                    Unittest code is added for this class instead of OmniSwitchTelnetDriver class
    """

    def __init__(self, ip, platform, login='admin', password='switch', prompt='->'):
        super(OmniSwitchTelnetDriverTestClass, self).__init__(ip, platform, login, password, prompt)
        self.commands = []

    def is_connected(self):
        return True

    def disconnect(self):
        pass

    def set_switch_type(self, m_type):
        self.switch_type = m_type

    def get_commands(self):
        return self.commands

    def clean_commands(self):
        self.commands = []

    # store command
    def send_command(self, command):
        self.commands.append(command)
        return True
