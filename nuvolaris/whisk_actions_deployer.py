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
# wsk project deploy --project deploy/whisk-system —-apihost http://localhost:3233 --auth 789c46b1-71f6-4ed5-8c54-816aa4f8c502:abczO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP
#

import logging
import json
import nuvolaris.config as cfg
import nuvolaris.template as ntp
import nuvolaris.util as util
import nuvolaris.kustomize as kust
import os

from nuvolaris.whisk_system_util import WhiskSystemClient
from nuvolaris.util import nuv_retry
from subprocess import CompletedProcess

def prepare_system_actions_data():
    data = {}
    
    couchdb_host = cfg.get("couchdb.host") or "couchdb"
    couchdb_port = cfg.get("couchdb.port") or "5984"

    globals=[]
    globals.append({"key":"couchdb_user", "value":cfg.get("couchdb.admin.user", "COUCHDB_ADMIN_USER", "whisk_admin")})
    globals.append({"key":"couchdb_password", "value":cfg.get("couchdb.admin.password", "COUCHDB_ADMIN_PASSWORD", "some_passw0rd")})
    globals.append({"key":"couchdb_host", "value":couchdb_host})
    globals.append({"key":"couchdb_port", "value":couchdb_port})
    data = {
        "globals":globals
    }

    return data

def process_wsk_result(result: CompletedProcess, expected_success_msg: str):
    """
    Parses a subprocess.CompletedProcess object and raises an exception if the
    returncode != 0 or the stdout response does not contains the expected message.
    Raising an Exception forces a retry if the @nuv_retry decorator is used.
    """
    has_error = False
    logging.debug(f"expected message for success {expected_success_msg}")

    returncode = result.returncode
    output = result.stdout.decode()
    error = result.stderr.decode()

    if returncode != 0:
        logging.warn(f"error {error} detected when deploying system action")
        has_error = True

    if not expected_success_msg in output:
        logging.warn(f"response {output} does not contains the expected result {expected_success_msg}")
        has_error = True

    if has_error:
        logging.warn(f"could not validate wsk response {result}")
        raise Exception("whisk system action deployement failure. Forcing a retry")

    logging.info(f"successfully validated wsk response {result}")

@nuv_retry()
def safe_deploy(wskClient):
    logging.info("*** deploying deploy/whisk-system project")

    deployProjectResponse = wskClient.wsk("project","deploy","--project","deploy/whisk-system")
    process_wsk_result(deployProjectResponse, "Success")

    actionListResult = wskClient.wsk("action","list") 
    process_wsk_result(actionListResult, "whisk-system/nuv/login")

    return True

def deploy_whisk_system_action():
    auth = cfg.get('openwhisk.namespaces.whisk-system')
    data = prepare_system_actions_data()
    tplres = kust.processTemplate("whisk-system","whisk-system-manifest-tpl.yaml",data,"manifest.yaml")

    wskClient = WhiskSystemClient(auth)
    result = safe_deploy(wskClient)
    return result
