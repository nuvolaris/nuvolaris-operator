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
import json
import nuvolaris.config as cfg
import nuvolaris.template as ntp
import nuvolaris.util as util
import nuvolaris.kustomize as kust
import os
from nuvolaris.whisk_system_util import WhiskSystemClient

def prepare_system_actions_data():
    data = {}

    globals=[]
    globals.append({"key":"couchdb_user", "value":cfg.get("couchdb.admin.user", "COUCHDB_ADMIN_USER", "whisk_admin")})
    globals.append({"key":"couchdb_password", "value":cfg.get("couchdb.admin.password", "COUCHDB_ADMIN_PASSWORD", "some_passw0rd")})
    globals.append({"key":"couchdb_host", "value":cfg.get("couchdb.host", "COUCHDB_SERVICE_HOST", "couchdb")})
    globals.append({"key":"couchdb_port", "value":cfg.get("couchdb.port", "COUCHDB_SERVICE_PORT", "5984")})
    data = {
        "globals":globals
    }

    return data

def deploy_whisk_system_action():
    auth = cfg.get('openwhisk.namespaces.whisk-system')
    try:
        wskClient = WhiskSystemClient(auth)

        data = prepare_system_actions_data()
        tplres = kust.processTemplate("whisk-system","whisk-system-manifest-tpl.yaml",data,"manifest.yaml")
        res = util.check(wskClient.wskdeploy("-p","deploy/whisk-system"),"deploy_whisk_system_action",True)
        return res
    except Exception as e:
        logging.error(e)
        return False 
