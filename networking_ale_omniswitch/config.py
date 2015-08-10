#!/bin/env python
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


from oslo_config import cfg

device_opts = [
    cfg.ListOpt('omni_edge_devices', default=[], help=""),
    cfg.ListOpt('omni_core_devices', default=[], help=""),
    cfg.StrOpt('dhcp_server_interface', default='', help=""),
    cfg.IntOpt('switch_save_config_interval', default=600, help="")
]

cfg.CONF.register_opts(device_opts, "ml2_ale_omniswitch")
