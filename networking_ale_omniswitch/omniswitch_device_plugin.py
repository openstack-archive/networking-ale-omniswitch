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

from eventlet import GreenPool as Pool
from oslo_config import cfg

from networking_ale_omniswitch import config  # noqa
from networking_ale_omniswitch import omniswitch_constants as omni_const
from networking_ale_omniswitch.omniswitch_restful_driver import OmniSwitchRestfulDriver
from networking_ale_omniswitch.omniswitch_telnet_driver import OmniSwitchTelnetDriver


LOG = logging.getLogger(__name__)


class OmniSwitchDevicePluginV2(object):

    """Name:     OmniSwitchDevicePluginV2
    Description: OpenStack Neutron plugin for Alcatel-Lucent OmniSwitch Data networking
                 devices.

    Details:     It is one of the device plugin in the OmniSwitch multi-plugin design.
                 This implements the Neutron Network APIs (ver 2.0) for OmniSwitch
                 devices. This is instantiated by the OmniSwitchNetworkPluginV2 which is
                 core plugin for Neutron server. This uses the device specific
                 communication mechanism for interfacing with different types of
                 OmniSwitch devices.
    """

    def __init__(self):

        # list of omni devices from 'omni_network_plugin.ini' file
        self.edge_device_list = []
        # list of device driver instances (ddi) corresponding to each of the device in edge_device_list
        self.edge_ddi_list = {}
        # list of omni core devices from 'omni_network_plugin.ini' file
        self.core_device_list = []
        # list of device driver instances (ddi) corresponding to each of the device in core_device_list
        self.core_ddi_list = {}
        # details of the edge switch which is connected to network node where dhcp-server is running
        self.dhcp_service = []
        self.dhcp_if_inst = None
        # interval(in secs) at which the config will be saved in the switches
        self.switch_save_config_interval = 0

        # some init general init status vars
        self.db_option = None
        self.init_config_applied = None

        # used for tracking whether to do write memory in the switch or not
        self.edge_config_changed = 0
        self.core_config_changed = 0

        self._load_config()
        self._load_edge_ddi()
        self._load_core_ddi()
        self._load_dhcp_if_inst()
        self._start_save_config_thread()

    def _load_config(self):
        """loads the OmniSwitch device list from the config file and instantiates
        the appropriate device specific driver to communicate with it.
        """

        # OMNI_EDGE_DEVICES
        for device in cfg.CONF.ml2_ale_omniswitch.omni_edge_devices:
            device_specs = [x.strip() for x in device.split(':')]
            self.edge_device_list.append(device_specs)

        # OMNI_CORE_DEVICES
        if cfg.CONF.ml2_ale_omniswitch.omni_core_devices != [] and cfg.CONF.ml2_ale_omniswitch.omni_core_devices != ['']:
            for device in cfg.CONF.ml2_ale_omniswitch.omni_core_devices:
                device_specs = [x.strip() for x in device.split(':')]
                self.core_device_list.append(device_specs)

        # DHCP_SERVER_INTERFACE
        self.dhcp_service = [x.strip() for x in cfg.CONF.ml2_ale_omniswitch.dhcp_server_interface.split(':')]
        if self.dhcp_service == [] or self.dhcp_service == ['']:
            self.dhcp_service = None

        self.switch_save_config_interval = cfg.CONF.ml2_ale_omniswitch.switch_save_config_interval
        if (self.switch_save_config_interval < omni_const.OMNI_CFG_SAVE_INTERVAL_MIN or
           self.switch_save_config_interval > omni_const.OMNI_CFG_SAVE_INTERVAL_MAX):
            LOG.info("switch_save_config_interval %d is out of valid range(%d - %d)... default to %d",
                     self.switch_save_config_interval,
                     omni_const.OMNI_CFG_SAVE_INTERVAL_MIN,
                     omni_const.OMNI_CFG_SAVE_INTERVAL_MAX,
                     omni_const.OMNI_CFG_SAVE_INTERVAL_MIN)
            self.switch_save_config_interval = omni_const.OMNI_CFG_SAVE_INTERVAL_MIN

    def _load_edge_ddi(self):
        for device in self.edge_device_list:
            drv_type = self._get_driver_type(device[omni_const.OMNI_CFG_DEV_TYPE])

            if self.omniswitch_6xx(device):
                if self.device_access_rest(device):
                    LOG.info("ALERT: This device (%s) does not support REST interface.\
                          Instead TELNET interface will be used!", device[omni_const.OMNI_CFG_DEV_IP])
                self.edge_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                              OmniSwitchTelnetDriver(device[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                                     device[omni_const.OMNI_CFG_DEV_LOGIN],
                                                                     device[omni_const.OMNI_CFG_DEV_PASSWORD],
                                                                     device[omni_const.OMNI_CFG_DEV_PROMPT]))
            # for both 7XX and 8XX
            elif self.switch_access_rest(device):
                self.edge_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                              OmniSwitchRestfulDriver(device[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                                      device[omni_const.OMNI_CFG_DEV_LOGIN],
                                                                      device[omni_const.OMNI_CFG_DEV_PASSWORD]))
            else:
                self.edge_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                              OmniSwitchTelnetDriver(device[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                                     device[omni_const.OMNI_CFG_DEV_LOGIN],
                                                                     device[omni_const.OMNI_CFG_DEV_PASSWORD]))

        LOG.info("_load_edge_ddi done!")

    def _load_core_ddi(self):
        if len(self.core_device_list) == 0:
            return

        for device in self.core_device_list:
            drv_type = self._get_driver_type(device[omni_const.OMNI_CFG_DEV_TYPE])

            if self.omniswitch_6xx(device):
                if self.device_access_rest(device):
                    LOG.info("ALERT: This device (%s) does not support REST interface.\
                           Instead TELNET interface will be used!", device[omni_const.OMNI_CFG_DEV_IP])
                self.core_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                              OmniSwitchTelnetDriver(device[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                                     device[omni_const.OMNI_CFG_DEV_LOGIN],
                                                                     device[omni_const.OMNI_CFG_DEV_PASSWORD],
                                                                     device[omni_const.OMNI_CFG_DEV_PROMPT]))
            # for both 7XX and 8XX
            elif self.switch_access_rest(device):
                self.core_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                              OmniSwitchRestfulDriver(device[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                                      device[omni_const.OMNI_CFG_DEV_LOGIN],
                                                                      device[omni_const.OMNI_CFG_DEV_PASSWORD]))
            else:
                self.core_ddi_list.setdefault(device[omni_const.OMNI_CFG_DEV_IP],
                                              OmniSwitchTelnetDriver(device[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                                     device[omni_const.OMNI_CFG_DEV_LOGIN],
                                                                     device[omni_const.OMNI_CFG_DEV_PASSWORD]))
        LOG.info("_load_core_ddi done!")

    def _load_dhcp_if_inst(self):
        if not self.dhcp_service:
            return
        drv_type = self._get_driver_type(self.dhcp_service[omni_const.OMNI_CFG_DEV_TYPE])
        if self.omniswitch_6xx(self.dhcp_service):
            if self.device_access_rest(self.dhcp_service):
                LOG.info("ALERT: This device (%s) does not support REST interface.\
                       Instead TELNET interface will be used!", self.dhcp_service[omni_const.OMNI_CFG_DEV_IP])
            self.dhcp_if_inst = OmniSwitchTelnetDriver(self.dhcp_service[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                       self.dhcp_service[omni_const.OMNI_CFG_DEV_LOGIN],
                                                       self.dhcp_service[omni_const.OMNI_CFG_DEV_PASSWORD],
                                                       self.dhcp_service[omni_const.OMNI_CFG_DEV_PROMPT])
        else:  # for both 7XX and 8XX
            if self.device_access_rest(self.dhcp_service):
                self.dhcp_if_inst = OmniSwitchRestfulDriver(self.dhcp_service[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                            self.dhcp_service[omni_const.OMNI_CFG_DEV_LOGIN],
                                                            self.dhcp_service[omni_const.OMNI_CFG_DEV_PASSWORD])
            else:
                self.dhcp_if_inst = OmniSwitchTelnetDriver(self.dhcp_service[omni_const.OMNI_CFG_DEV_IP], drv_type,
                                                           self.dhcp_service[omni_const.OMNI_CFG_DEV_LOGIN],
                                                           self.dhcp_service[omni_const.OMNI_CFG_DEV_PASSWORD])

        LOG.info("_load_dhcp_if_inst done!")

    def _start_save_config_thread(self):
        SaveConfigThread(self).start()

    def _config_vpa_core(self, vlan_id, action, net_name=''):
        pool = Pool(size=(len(self.core_device_list) + len(self.edge_device_list)))

        def config_vpa_core_device(device):
            if device[omni_const.OMNI_CFG_DEV_CORE_IF].strip():
                if action == omni_const.OMNI_CFG_CREATE:
                    self.core_ddi_list[device[omni_const.OMNI_CFG_DEV_IP]].create_vlan_locked(vlan_id, net_name)
                    if_list = device[omni_const.OMNI_CFG_DEV_CORE_IF].split(' ')
                    for port in if_list:
                        self.core_ddi_list[device[omni_const.OMNI_CFG_DEV_IP]].create_vpa(vlan_id, port)
                elif action == omni_const.OMNI_CFG_UPDATE:
                    self.core_ddi_list[device[omni_const.OMNI_CFG_DEV_IP]].update_vlan_locked(vlan_id, net_name)
                elif action == omni_const.OMNI_CFG_DELETE:
                    LOG.info("vpa core delete vlan!")
                    self.core_ddi_list[device[omni_const.OMNI_CFG_DEV_IP]].delete_vlan_locked(vlan_id)

        def config_vpa_edge_device(device):
            if device[omni_const.OMNI_CFG_DEV_EDGE2CORE_IF].strip():
                if_list = device[omni_const.OMNI_CFG_DEV_EDGE2CORE_IF].split(' ')
                for port in if_list:
                    self.edge_ddi_list[device[omni_const.OMNI_CFG_DEV_IP]].create_vpa(vlan_id, port)

        output = list()
        for result in pool.imap(config_vpa_core_device, self.core_device_list):
            output.append(result)
        if action == omni_const.OMNI_CFG_CREATE:
            for result in pool.imap(config_vpa_edge_device, self.edge_device_list):
                output.append(result)
        return True

    def _config_vpa_edge(self, edge_ddi_obj, vlan_id, action):
        compute_if = self._get_edge2compute_if(edge_ddi_obj.get_ip())
        if compute_if.strip():
            if_list = compute_if.split(' ')
            for port in if_list:
                if action == omni_const.OMNI_CFG_CREATE:
                    edge_ddi_obj.create_vpa(vlan_id, port)
                elif action == omni_const.OMNI_CFG_DELETE:
                    edge_ddi_obj.delete_vpa(vlan_id, port)

        return True

    """
       General System APIs within Device plugin
    """

    def save_core_config(self, immediate=0):
        if immediate == 0:
            self.core_config_changed = 1
            return

        pool = Pool(size=len(self.core_device_list))

        def m_save_core_config(device):
            ddi_obj = self.core_ddi_list[device[omni_const.OMNI_CFG_DEV_IP]]
            self._invoke_driver_api(ddi_obj, "save_config", [])

        output = list()
        for result in pool.imap(m_save_core_config, self.core_device_list):
            output.append(result)

        self.core_config_changed = 0
        return

    def save_edge_config(self, immediate=0):
        if immediate == 0:
            self.edge_config_changed = 1
            return

        pool = Pool(size=len(self.edge_device_list))

        def m_save_edge_config(device):
            ddi_obj = self.edge_ddi_list[device[omni_const.OMNI_CFG_DEV_IP]]
            self._invoke_driver_api(ddi_obj, "save_config", [])

        output = list()
        for result in pool.imap(m_save_edge_config, self.edge_device_list):
            output.append(result)

        self.edge_config_changed = 0
        return

    def save_config(self):
        if self.core_config_changed == 1:
            self.save_core_config(1)

        if self.edge_config_changed == 1:
            self.save_edge_config(1)

    """ Neutron Core API 2.0 """

    def create_network(self, mech_context):
        ret = False
        if self.cn_edge_config(mech_context):
            if self.cn_core_config(mech_context):
                ret = self.cn_dhcp_config(mech_context)
        return ret

    def update_network(self, mech_context):
        self.un_edge_config(mech_context)
        self.un_core_config(mech_context)
        self.un_dhcp_config(mech_context)
        return True

    def delete_network(self, mech_context):
        self.dn_dhcp_config(mech_context)
        self.dn_core_config(mech_context)
        self.dn_edge_config(mech_context)
        return True

    def update_subnet(self, mech_context):
        return True

    def create_subnet(self, mech_context):
        return True

    def delete_subnet(self, mech_context):
        return True

    def delete_port(self, mech_context):
        return True

    def update_port(self, mech_context):
        return True

    def create_port(self, mech_context):
        return True

    """
       Wrapper for Core API functional routines
    """
    def cn_edge_config(self, mech_context):
        ret = True
        network = mech_context.current
        segments = mech_context.network_segments

        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']
        network_name = network['name']

        def m_cn_edge_config(ddi_obj):
            if self._invoke_driver_api(ddi_obj, "create_network", [vlan_id, network_name]):
                res = self._config_vpa_edge(ddi_obj, vlan_id, omni_const.OMNI_CFG_CREATE)
            else:
                res = False
            return res

        pool = Pool(size=len(self.edge_ddi_list.items()))
        output = list()

        ddi_list = [item[1] for item in self.edge_ddi_list.items()]
        for result in pool.imap(m_cn_edge_config, ddi_list):
            output.append(result)

        if False in output:
            # some error in create network, roll back network creation
            self.delete_network(mech_context)  # vad: optimize only for that switch
            self.save_edge_config()
            ret = False

        return ret

    def cn_core_config(self, mech_context):
        ret = True
        network = mech_context.current
        segments = mech_context.network_segments

        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']
        network_name = network['name']

        if not self._config_vpa_core(vlan_id, omni_const.OMNI_CFG_CREATE, network_name):
                # some error in vpa creation, roll back network creation
                self.delete_network(mech_context)
                self.save_edge_config()
                ret = False
        else:
            self.save_core_config()
        return ret

    def cn_dhcp_config(self, mech_context):
        ret = True
        segments = mech_context.network_segments
        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']

        if self.dhcp_if_inst:
            ret = self.dhcp_if_inst.create_vpa(vlan_id, self.dhcp_service[omni_const.OMNI_CFG_DHCP_SERVER_IF])
            if not ret:
                # some error in vpa creation for dhcp, roll back network creation
                self.delete_network(mech_context)
                ret = False

        self.save_edge_config()
        return ret

    def un_edge_config(self, mech_context):
        ret = True
        network = mech_context.current
        segments = mech_context.network_segments

        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']
        network_name = network['name']

        if network_name == '':
            LOG.error("un_edge_config: update network: network cannot be the empty string!")
            return False

        def m_un_edge_config(ddi_obj):
            res = True
            if not self._invoke_driver_api(ddi_obj, "update_network", [vlan_id, network_name]):
                res = False
            if not res:
                LOG.info("update network edge failed")
                return res

        output = list()
        pool = Pool(size=len(self.edge_ddi_list.items()))
        ddi_list = [item[1] for item in self.edge_ddi_list.items()]

        for result in pool.imap(m_un_edge_config, ddi_list):
            output.append(result)
        if False in output:
            ret = False

        self.save_edge_config()
        return ret

    def un_core_config(self, mech_context):
        ret = True
        network = mech_context.current
        segments = mech_context.network_segments

        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']
        network_name = network['name']

        if network_name == '':
            LOG.error("un_core_config: update network: network cannot be the empty string!")
            return False

        if not self._config_vpa_core(vlan_id, omni_const.OMNI_CFG_UPDATE, network_name):
            LOG.error("un_core_config: update network core failed")
            ret = False
        else:
            self.save_core_config()
        return ret

    def un_dhcp_config(self, mech_context):
        ret = True
        if not self.dhcp_if_inst:
            return ret

        network = mech_context.current
        segments = mech_context.network_segments

        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']
        network_name = network['name']

        if network_name == '':
            LOG.error("un_dhcp_config: network cannot be the empty string!")
            return False

        if not self._invoke_driver_api(self.dhcp_if_inst, "update_network", [vlan_id, network_name]):
            LOG.error("un_dhcp_config: update network failed!")
            ret = False

        self.save_edge_config()
        return ret

    def dn_edge_config(self, mech_context):
        ret = True
        segments = mech_context.network_segments

        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']

        def m_dn_edge_config_vlan(ddi_obj):
            self._config_vpa_edge(ddi_obj, vlan_id, omni_const.OMNI_CFG_DELETE)
            self._invoke_driver_api(ddi_obj, "delete_network", [vlan_id])

        pool = Pool(size=len(self.edge_ddi_list.items()))
        output = list()
        ddi_list = [item[1] for item in self.edge_ddi_list.items()]
        for result in pool.imap(m_dn_edge_config_vlan, ddi_list):
            output.append(result)

        self.save_edge_config()
        return ret

    def dn_core_config(self, mech_context):
        ret = True
        segments = mech_context.network_segments
        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']

        if not self._config_vpa_core(vlan_id, omni_const.OMNI_CFG_DELETE):
            ret = False
        else:
            self.save_core_config()
        return ret

    def dn_dhcp_config(self, mech_context):
        segments = mech_context.network_segments
        # currently supports only one segment per network
        segment = segments[0]
        vlan_id = segment['segmentation_id']

        if self.dhcp_if_inst:
            return self.dhcp_if_inst.delete_vpa(vlan_id, self.dhcp_service[omni_const.OMNI_CFG_DHCP_SERVER_IF])
        return True

    """
       Utility routines related to CONFIG
    """
    def _get_edge2compute_if(self, dev_ip):
        for device in self.edge_device_list:
            if device[omni_const.OMNI_CFG_DEV_IP] == dev_ip:
                return device[omni_const.OMNI_CFG_DEV_EDGE2COMPUTE_IF]

    def _get_driver_type(self, switch_type):
        if switch_type == omni_const.OMNISWITCH_OS6860:
            return omni_const.OMNISWITCH_8XX
        elif switch_type == omni_const.OMNISWITCH_OS6900 or switch_type == omni_const.OMNISWITCH_OS10K:
            return omni_const.OMNISWITCH_7XX
        elif (switch_type == omni_const.OMNISWITCH_OS6850E or
              switch_type == omni_const.OMNISWITCH_OS6855 or
              switch_type == omni_const.OMNISWITCH_OS6450 or
              switch_type == omni_const.OMNISWITCH_OS9000):
            return omni_const.OMNISWITCH_6XX

    def _get_switch_access_method(self, switch_access_method):
        return switch_access_method if switch_access_method != "" else omni_const.OMNI_CFG_SWITCH_ACCESS_TELNET

    def _invoke_driver_api(self, drvobj, function_name, args):
        # return thread.start_new_thread(getattr(drvobj, function_name), tuple(args))
        return getattr(drvobj, function_name)(*args)

    def omniswitch_8xx(self, device):
        drv_type = self._get_driver_type(device[omni_const.OMNI_CFG_DEV_TYPE])
        return drv_type == omni_const.OMNISWITCH_8XX

    def omniswitch_7xx(self, device):
        drv_type = self._get_driver_type(device[omni_const.OMNI_CFG_DEV_TYPE])
        return drv_type == omni_const.OMNISWITCH_7XX

    def omniswitch_6xx(self, device):
        drv_type = self._get_driver_type(device[omni_const.OMNI_CFG_DEV_TYPE])
        return drv_type == omni_const.OMNISWITCH_6XX

    def device_access_rest(self, device):
        return device[omni_const.OMNI_CFG_DEV_ACCESS_METHOD] == omni_const.OMNI_CFG_SWITCH_ACCESS_REST

    def device_access_telnet(self, device):
        return device[omni_const.OMNI_CFG_DEV_ACCESS_METHOD] == omni_const.OMNI_CFG_SWITCH_ACCESS_TELNET

    def switch_access_rest(self, device):
        switch_access_method = self._get_switch_access_method(device[omni_const.OMNI_CFG_DEV_ACCESS_METHOD])
        return switch_access_method == omni_const.OMNI_CFG_SWITCH_ACCESS_REST

    def switch_access_telnet(self, device):
        switch_access_method = self._get_switch_access_method(device[omni_const.OMNI_CFG_DEV_ACCESS_METHOD])
        return switch_access_method == omni_const.OMNI_CFG_SWITCH_ACCESS_TELNET


""" Save config thread class """


class SaveConfigThread(threading.Thread):
    plugin_obj = None

    def __init__(self, plugin_obj):
        self.plugin_obj = plugin_obj
        threading.Thread.__init__(self)
        self.event = threading.Event()

    def run(self):
        if self.plugin_obj is None:
            LOG.info("Plugin Object is Null, SaveConfigThread is terminated!")
            self.stop()
            return

        while not self.event.is_set():
            # print "do something %s" % time.asctime(time.localtime(time.time()))
            # self.event.wait( 1 )
            self.plugin_obj.save_config()
            # LOG.info("run: %s", time.asctime(time.localtime(time.time())))
            self.event.wait(self.plugin_obj.switch_save_config_interval)

    def stop(self):
        self.event.set()
