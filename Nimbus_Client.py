'''
Created on Apr 21, 2015

@author: mvisco
'''
from keystoneclient import session
from keystoneclient.auth.identity import v2
from keystoneclient.v2_0 import client as keystoneclient
from neutronclient.v2_0 import client as neutronclient
from novaclient.v2 import client as novaclient
import datetime
import logging

LOGGER = logging.getLogger(__name__)

class NimbusClient(object):
    '''
    Client for accessing Nimbus APIs
    '''
    nova = None
    neutron = None
    tenant_id = None
    NOVA_API_VERSION = 2

    def __init__(self, auth_url, username, password, tenant_id):
        self.tenant_id = tenant_id
        # Neutron setup
        keystone = keystoneclient.Client(auth_url=auth_url, username=username,
                                   password=password, tenant_id=tenant_id)
        endpoint_url = keystone.service_catalog.url_for(service_type="network")
        token = keystone.auth_token

        self.neutron = neutronclient.Client(endpoint_url=endpoint_url,
                                            auth_url=auth_url, token=token,
                                            tenant_id=tenant_id)

        # Nova setup
        auth = v2.Password(auth_url=auth_url, username=username,
                           password=password, tenant_id=tenant_id)
        sess = session.Session(auth=auth)
        self.nova = novaclient.Client(self.NOVA_API_VERSION, session=sess,
                                      connection_pool=True)

    def get_servers(self, search_opts=None):
        '''
        Get dict of all servers from Nimbus, key of instance-id, value of
        dictionary containing server info
        '''
        server_dict = {}
        servers = self.nova.servers.list(search_opts=search_opts)
        LOGGER.debug('{} servers found in tenant {}'
                     .format(len(servers), self.tenant_id))
        for server in servers:
            instance_id = server.id
            server_dict[instance_id] = server.to_dict()
        return server_dict

    def get_usage(self):
        '''
        Return dict of tenant usage, key of instance-id, value of usage dict
        '''
        usage_dict = {}
        start = datetime.datetime.now()
        end = start + datetime.timedelta(seconds=1)
        usage = self.nova.usage.get(tenant_id=self.tenant_id, start=start,
                                    end=end)
        usage = usage.to_dict()['server_usages']
        for server in usage:
            usage_dict[server['instance_id']] = server
        return usage_dict

    def get_server_hosts(self):
        '''
        Return dict of servers and the hosts they run on, key of host_id, value
        is a list of tuples (name, instance_id) representing each server
        running on that host
        '''
        hosts_dict = {}
        servers = self.get_servers()
        for server_info in servers.itervalues():
            host_id = server_info['hostId']
            if not hosts_dict.get(host_id):
                hosts_dict[host_id] = []
            hosts_dict[host_id].append((server_info.get('name'),
                                        server_info.get('id')))
        return hosts_dict

    def get_networks(self):
        '''
        Return list of dicts containing details of all tenant networks
        '''
        networks = self.neutron.list_networks()
        return networks.get('networks')