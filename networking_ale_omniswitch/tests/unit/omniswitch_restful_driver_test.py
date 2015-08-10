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


from networking_ale_omniswitch.omniswitch_restful_driver import OmniSwitchRestfulDriver


class OmniSwitchRestfulDriverTestClass(OmniSwitchRestfulDriver):
    """Name:           OmniSwitchRestfulDriverTestClass
    Description:    OmniSwitchRestfulDriverTestClass only serves the purpose of implementing unittest for
                    OmniSwitchRestfulDriver (omniswitch_restful_driver.py) module
    Details:        Since OmniSwitchRestfulDriver uses telnet urllib2 to send mib object
                    via http methods(get, put, post, etc.) to real device, we cannot directly add unittest for it.
                    The OmniSwitchRestfulDriverTestClass is created to stub the http methods operation
                    of OmniSwitchRestfulDriver and store mib ojects to local self.aosapi member variable
                    Unittest code is added for this class instead of OmniSwitchRestfulDriver class
    """

    def __init__(self, ip, platform, login='admin', password='switch', prompt='->'):
        super(OmniSwitchRestfulDriverTestClass, self).__init__(ip, platform, login, password, prompt)
        self.aosapi = AOSAPITestClas(self.switch_ip)

    def get_objects(self):
        return self.aosapi.get_objects()

    def clean_objects(self):
        return self.aosapi.clean_objects()

    def _log_results(self, cmd_type, domain, urn, args, cmd_desc,
                     was_successful, results, log_success=True, log_failure=True):
        return True

    def set_switch_type(self, m_type):
        self.switch_type = m_type


class AOSAPITestClas(object):

    def __init__(self, switch_ip):
        self.domains = []
        self.tables = []
        self.objects = []
        self.switch_ip = switch_ip

    def login(self):
        pass

    def logout(self):
        pass

    def query(self, domain, urn='', args={}):
        self.domains.append(domain)
        self.tables.append(urn)
        self.objects.append(args)
        return {'result': 'test'}

    def post(self, domain, urn='', args={}):
        self.domains.append(domain)
        self.tables.append(urn)
        self.objects.append(args)
        return {'result': 'test'}

    def put(self, domain, urn='', args={}):
        self.domains.append(domain)
        self.tables.append(urn)
        self.objects.append(args)
        return {'result': 'test'}

    def delete(self, domain, urn='', args={}):
        self.domains.append(domain)
        self.tables.append(urn)
        self.objects.append(args)
        return {'result': 'test'}

    def get_objects(self):
        return self.objects

    def success(self):
        return True

    def clean_objects(self):
        self.objects = []
