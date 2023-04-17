# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
import logging

from backoff import expo, on_exception
from requests import get
from requests.exceptions import RequestException

# The maximum amount of tries to attempt when making API calls.
MAX_TRIES = 3

class IpUtil:
    _machine_ip = None

    def __init__(self):
        self.IPIFY_API_URI = 'https://api.ipify.org'
        self.IFCONFIG_API_URI = 'https://ifconfig.me/ip'     
        self.IP_INFO_API_URI = 'https://ipinfo.io/ip'
        self.IDENT_ME_API_URI = 'https://ident.me/'
        self.USER_AGENT = 'nuvolaris-ip-resolver'
        # The maximum amount of tries to attempt when making API calls.
        self.MAX_TRIES = 3

    @on_exception(expo, RequestException, max_tries=MAX_TRIES)
    def _get_ip_resp(self,api_uri: str):
        """
        Internal function which attempts to retrieve this machine's public IP
        address from a service running at the given api_uri parameter.
        :rtype: obj
        :returns: The response object from the HTTP request.
        :raises: RequestException if something bad happened and the request wasn't
            completed.
        .. note::
            If an error occurs when making the HTTP request, it will be retried
            using an exponential backoff algorithm.  This is a safe way to retry
            failed requests without giving up.
        """
        logging.debug(f"querying ip from {api_uri}")
        return get(api_uri, headers={'user-agent': self.USER_AGENT})

    def handle_ip_request(self,url):
        """
        Query a public api retuning the machine's public ip address
        >>> from nuvolaris.ip_util import IpUtil
        >>> ip_util = IpUtil()
        >>> ipify_ip = ip_util.handle_ip_request('https://api.ipify.org')
        >>> ifconfig_ip = ip_util.handle_ip_request('https://ifconfig.me/ip')
        >>> ifinfo_ip = ip_util.handle_ip_request('https://ipinfo.io/ip')
        >>> identme_ip = ip_util.handle_ip_request('https://ident.me/')
        >>> ipify_ip == ifconfig_ip
        True
        >>> ipify_ip == ifinfo_ip
        True
        >>> ipify_ip == identme_ip
        True
        """
        try:
            resp = self._get_ip_resp(url)
        except RequestException as e:
            logging.error(e)
            return None

        if resp.status_code != 200:
            logging.error('Received an invalid status code from ip service:' + str(resp.status_code) + '. The service might be experiencing issues.')
            return None

        return resp.text      

    def get_ip_chain(self, url):
        if not self._machine_ip:
           self._machine_ip = self.handle_ip_request(url)
        else :
            logging.info(f"current ip address {self._machine_ip}")

    def get_public_ip(self):
       """
        Attempt to get the machine public ip
        >>> from nuvolaris.ip_util import IpUtil
        >>> ip_util = IpUtil()
        >>> ip = ip_util.get_public_ip()
        >>> ip != None
        True
        >>> ipify_ip = ip_util.handle_ip_request('https://api.ipify.org')
        >>> ip == ipify_ip
        True
       """
       self.get_ip_chain(self.IPIFY_API_URI)
       self.get_ip_chain(self.IFCONFIG_API_URI)
       self.get_ip_chain(self.IP_INFO_API_URI)
       self.get_ip_chain(self.IDENT_ME_API_URI)

       return self._machine_ip
   