#    (c) Copyright 2013 Hewlett-Packard Development Company, L.P.
#    (c) Copyright 2015 Cisco Systems Inc.
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from neutron.tests.unit.extensions import test_l3 as test_l3_plugin
from neutron_lib import constants as lib_constants
from neutron_lib import context
from neutron_lib.plugins import constants as nconstants
from neutron_lib.plugins import directory
from neutron_vpnaas.db.vpn.vpn_ext_gw_db import VPNExtGWPlugin_db
from neutron_vpnaas.services.vpn.common import constants as v_constants
from neutron_vpnaas.tests import base
from neutron_vpnaas.tests.unit.db.vpn.test_vpn_db import NeutronResourcesMixin


class TestVpnCorePlugin(test_l3_plugin.TestL3NatIntPlugin):
    def __init__(self, configfile=None):
        super(TestVpnCorePlugin, self).__init__()


class TestVPNExtGwDB(base.NeutronDbPluginV2TestCase, NeutronResourcesMixin):
    def setUp(self):
        self.plugin_str = ('neutron_vpnaas.tests.unit.db.vpn.'
                           'test_vpn_ext_gw_db.TestVpnCorePlugin')
        super(TestVPNExtGwDB, self).setUp(self.plugin_str)

        self.core_plugin = directory.get_plugin()
        self.l3_plugin = directory.get_plugin(nconstants.L3)
        self.tenant_id = 'tenant1'
        self.context = context.get_admin_context()

    def _create_gw_port(self, router):
        port = {'port': {
            'tenant_id': self.tenant_id,
            'network_id': router['external_gateway_info']['network_id'],
            'fixed_ips': lib_constants.ATTR_NOT_SPECIFIED,
            'mac_address': lib_constants.ATTR_NOT_SPECIFIED,
            'admin_state_up': True,
            'device_id': router['id'],
            'device_owner': v_constants.DEVICE_OWNER_VPN_ROUTER_GW,
            'name': ''
        }}
        return self.core_plugin.create_port(self.context, port)

    def test_create_gateway(self):
        private_subnet, router = self.create_basic_topology()
        gateway = {'gateway': {
            'router_id': router['id'],
            'tenant_id': self.tenant_id
        }}
        gwdb = VPNExtGWPlugin_db()
        new_gateway = gwdb.create_gateway(self.context, gateway)
        expected = {**gateway['gateway'],
                    'status': lib_constants.PENDING_CREATE}
        self.assertDictSupersetOf(expected, new_gateway)

    def test_update_gateway_with_external_port(self):
        private_subnet, router = self.create_basic_topology()
        gwdb = VPNExtGWPlugin_db()
        # create gateway
        gateway = {'gateway': {
            'router_id': router['id'],
            'tenant_id': self.tenant_id
        }}
        new_gateway = gwdb.create_gateway(self.context, gateway)

        # create external port and update gateway with the port id
        gw_port = self._create_gw_port(router)
        gateway_update = {'gateway': {
            'gw_port_id': gw_port['id']
        }}
        gwdb.update_gateway(self.context, new_gateway['id'], gateway_update)

        # check that get_vpn_gw_dict_by_router_id includes external_fixed_ips
        found_gateway = gwdb.get_vpn_gw_dict_by_router_id(self.context,
                                                          router['id'])
        self.assertIn('external_fixed_ips', found_gateway)
        expected = sorted(gw_port['fixed_ips'])
        returned = sorted(found_gateway['external_fixed_ips'])
        self.assertEqual(returned, expected)

    def test_delete_gateway(self):
        private_subnet, router = self.create_basic_topology()
        gwdb = VPNExtGWPlugin_db()
        # create gateway
        gateway = {'gateway': {
            'router_id': router['id'],
            'tenant_id': self.tenant_id
        }}
        new_gateway = gwdb.create_gateway(self.context, gateway)
        self.assertIsNotNone(new_gateway)
        deleted = gwdb.delete_gateway(self.context, new_gateway['id'])
        self.assertEqual(deleted, 1)
        deleted = gwdb.delete_gateway(self.context, new_gateway['id'])
        self.assertEqual(deleted, 0)
        found_gateway = gwdb.get_vpn_gw_dict_by_router_id(self.context,
                                                          router['id'])
        self.assertIsNone(found_gateway)
