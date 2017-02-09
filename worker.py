'''
Created on Apr 19, 2015

@author: mvisco
'''
import threading
import time
import yaml
from novaclient.client import Client
import nimbus_access
import os
from fabric.api import local, env
from fabric.context_managers import settings
from fabric.operations import sudo
import logging

class Worker (threading.Thread):
    
    def __init__(self, angel, host_name):
        threading.Thread.__init__(self)
        self.angel = angel
        self.host_name = host_name
                
    def run(self):
        logging.info( "Starting Thread "+ self.name)
        logging.info( " I am a worker of Angel "+ self.angel.host_name)
       
        f = open('config.yaml')
        dataMap = yaml.safe_load(f)    
        user = dataMap['user']
        domain_name = dataMap['domain_name']
        datacenter = dataMap['datacenter']
        network_addr = datacenter + '-internal'
        f.close()
        host = self.host_name+'-'+domain_name
        # REMEMBER in order to have this stuff runninng from sigma directory you had to modify some paths in api.py and product.py
        # because they assume that stuff runs from bootstrap directory.
        
        cred_dict =nimbus_access(datacenter).get_access_api_info()
        version = '2'
        client=Client(version, cred_dict['user'], cred_dict['password'], cred_dict['tenant'], cred_dict['auth'])
        server=client.servers.find(name=self.host_name)
        dict_server = server.to_dict()
        addresses = dict_server['addresses']
        ip_address = addresses[network_addr][0]['addr']
        # eliminate unicode symbol
        ip_address = str(ip_address)
        
        #TODO for bastion should be different......       
        connect_string =  "{}@{}".format(user, ip_address)
        
        #using bastion as proxy
        gateway_string = dataMap['bastion_string']
        env.gateway = gateway_string
        env.disable_known_hosts = True
        
        key_file = [os.path.expanduser('~/.ssh/ops1'),
                                  os.path.expanduser('~/.ssh/id_rsa'),
                                  os.path.expanduser('~/.ssh/public_rsa')]      
        
        with settings(
                  warn_only=True,
                  host_string=connect_string,
                  key_filename= key_file,
                  forward_agent=True):
            result = sudo('traceroute cisco.com')
            logging.info( 'result of traceroute is '+ result)
        
        
        self.angel.callback(self.name)
        