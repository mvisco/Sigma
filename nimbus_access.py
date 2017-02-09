
import os
import sys
import getpass
import time
import hiera
import subprocess
import StringIO


class nimbus_access:
    def __init__(self, datacenter):
        self.dc = datacenter
        self.user = ""
        self.password = ""
        self.tenant = ""
        self.authurl = ""

    def _processing(self):
        # TODO read credentials from yaml file
        return

    def get_access_info(self):
        """
        Get access info to nimbus for issuing openstack cli based commands. It returns a string to be used directly in the cli command.
        """
        self._processing()
        nova_login = ' --os-username=\'{}\' --os-password=\'{}\' --os-tenant-name=\'{}\' --os-auth-url=\'{}\'' \
                     .format(self.user, self.password, self.tenant, self.authurl)
        return nova_login

    def get_access_api_info(self):
        """
        Get access info to nimbus for issuing openstack API based commands. It returns a dictionary.
        """
        self._processing()
        nova_login = {}
        nova_login['user'] = self.user
        nova_login['password'] = self.password
        nova_login['tenant'] = self.tenant
        nova_login['auth'] = self.authurl

        return nova_login

    def setenv(self):
        self._processing()
        os.environ['OS_USERNAME'] = self.user
        os.environ['OS_PASSWORD'] = self.password
        os.environ['OS_TENANT_NAME'] = self.tenant
        os.environ['OS_AUTH_URL'] = self.authurl

