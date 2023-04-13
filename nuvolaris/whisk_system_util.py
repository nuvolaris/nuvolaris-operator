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
import json
import subprocess
import nuvolaris.config as cfg
import nuvolaris.template as ntp
import nuvolaris.util as util
import os

class WhiskSystemClient:
    def __init__(self, auth):
        self.controller_host   = cfg.get("controller.host","CONTROLLER_HOST","controller")
        self.controller_port   = cfg.get("controller.port","CONTROLLER_PORT",3233)       
        self.admin_auth   = auth
        self.ow_host_url   = f"http://{self.controller_host}:{self.controller_port}"

        logging.info(f"Created a WhiskSystemClient instance pointing to {self.ow_host_url}")

    # wraps a wsk --apihost <> -u <auth> *kwargs
    def wsk(self, *kwargs):        
        cmd = ["wsk","--apihost",self.ow_host_url,"-u",self.admin_auth]
        cmd += list(kwargs)

        # executing
        logging.debug(cmd)
        try:
            res = subprocess.run(cmd, capture_output=True)

            returncode = res.returncode
            output = res.stdout.decode()
            error = res.stderr.decode()
            
            if returncode != 0:
                logging.error(error)
            else:
                logging.info(output)

            return returncode == 0
        except Exception as e:
            logging.error(e)
            return e           