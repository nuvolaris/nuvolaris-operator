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
# this module wraps a wsk client communicating with the internal OW controller using admin credentials 
import logging
import subprocess
import nuvolaris.config as cfg

class WhiskSystemClient:
    def __init__(self, auth):
        self.controller_host   = cfg.get("controller.host","OW_CONTROLLER_HOST","controller")
        self.controller_port   = cfg.get("controller.port","OW_CONTROLLER_PORT",3233)       
        self.admin_auth   = auth
        self.ow_host_url   = f"http://{self.controller_host}:{self.controller_port}"

        logging.info(f"Created a WhiskSystemClient instance pointing to {self.ow_host_url}")

    def wsk(self, *kwargs):
        """
        wraps a wsk --apihost <> -u <auth> *kwargs
        returns CompletedProcess response which resemble to something like
        CompletedProcess(args=['sdsad','sdsads'], returncode=0, stdout=b'Success: Deployment completed successfully.\n', stderr=b'')
        """
        cmd = ["wsk","--apihost",self.ow_host_url,"--auth",self.admin_auth]
        cmd += list(kwargs)

        # executing
        logging.debug(cmd)
        return subprocess.run(cmd, capture_output=True)
        