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
#
# Deploys a standalone mongodb
#

import kopf, json, time
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.util as util
import logging

def create(owner=None):
    """
    Deploys the mongodb operator and wait for the operator to be ready.
    """
    logging.info("*** creating mongodb-standalone")    
    exposed = cfg.get('mongodb.exposedExternally') or False 

    data = util.get_mongodb_config_data()
    mkust = kus.patchTemplates("mongodb-standalone", ["mongodb-auth.yaml","mongodb-cm.yaml","mongodb-sts.yaml"], data)
    mkust += kus.patchPersistentVolumeClaim("mongodb-data","/spec/resources/requests/storage",f"{data['size']}Gi")
    mspec = kus.kustom_list("mongodb-standalone", mkust, templates=[], data=data)

    if owner:
        kopf.append_owner_reference(mspec['items'], owner)
    else:
        cfg.put("state.mongodb.spec", mspec)
    
    res = kube.apply(mspec)

    # dynamically detect mongodb pod and wait for readiness
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb')].metadata.name}")
 
    logging.info("*** created mongodb-standalone")    
    return res

def delete_by_owner():
    spec = kus.build("mongodb-standalone")
    res = kube.delete(spec)
    logging.info(f"delete mongodb: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.mongodb.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete mongodb: {res}")
    
    return res

def delete(owner=None):
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()