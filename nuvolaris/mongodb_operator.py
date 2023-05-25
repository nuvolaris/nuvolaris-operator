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
# Containers can get the nuvolaris mongodb connection string
# deployed from the nuvolaris-operator using something similar to
#containers:
# - name: test-app
#   env:
#    - name: "CONNECTION_STRING"
#      valueFrom:
#        secretKeyRef:
#          name: nuvolaris-mongodb-nuvolaris-nuvolaris
#          key: connectionString.standardSrv
#
# WARNING connectionString.standardSrv it is normally a base64 endoded string
#
# Currently for development purposes it is possible to access mongodb by port forwarding
# kubectl -n nuvolaris port-forward service/nuvolaris-mongodb-svc 27017:27017
#

import kopf, json, time
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.util as util
import logging

def get_operator_pod_name():
    pods = kube.get_pods("name=mongodb-kubernetes-operator")
    items = list(pods['items'])    

    if(len(items)):
        item = items[0]
        return item['metadata']['name']
    
    return None

def create(owner=None):
    """
    Deploys the mongodb operator and wait for the operator to be ready.
    """
    logging.info("*** creating mongodb-operator")    
    admin_user = cfg.get('mongodb.admin.user') or "whisk_user"
    admin_pwd = cfg.get('mongodb.admin.password') or "0therPa55"
    nuv_user = cfg.get('mongodb.nuvolaris.user') or "nuvolaris"
    nuv_pwd = cfg.get('mongodb.nuvolaris.password') or "s0meP@ass3"
    exposed = cfg.get('mongodb.exposedExternally') or False 

    data = util.get_mongodb_config_data()

    spec = kus.kustom_list("mongodb-operator")

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.mongodb-operator.spec", spec)

    res = kube.apply(spec)
    logging.info("*** created mongodb operator")

    pod_name = get_operator_pod_name()
    #wait for mongodb_operator to be ready
    
    if( pod_name ):
        logging.info(f"checking for {pod_name}")
        while not kube.wait(f"pod/{pod_name}", "condition=ready"):
            logging.info(f"waiting for {pod_name} to be ready...")
            time.sleep(1)
        
        logging.info("*** creating a mongodb instance")
        
        tpl_filter =  ["mongodb-auth.yaml","mongodb-auth-nuvolaris.yaml","mongodb.yaml"]
        if exposed: 
            logging.info("*** including mongodb service for localhost access")
            tpl_filter.append("mongodb-svc.yaml")
        

        mkust = kus.patchTemplates("mongodb-operator-deploy", ["mongodb-auth.yaml","mongodb-auth-nuvolaris.yaml","mongodb-config.yaml"], data)    
        mspec = kus.restricted_kustom_list("mongodb-operator-deploy", mkust, templates=[],templates_filter=tpl_filter, data=data)

        if owner:
            kopf.append_owner_reference(mspec['items'], owner)
        else:
            cfg.put("state.mongodb.spec", mspec)
        
        res = kube.apply(mspec)
        # dynamically detect mongodb pod and wait for readiness
        util.wait_for_pod_ready("{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb-svc')].metadata.name}")
    else:
        logging.info("*** something went wrong deploying mongodb operator")    
    return res 


def delete_by_owner():
    spec = kus.build("mongodb-operator-deploy")
    res = kube.delete(spec)
    spec = kus.build("mongodb-operator")
    res = kube.delete(spec)
    logging.info(f"delete mongodb: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.mongodb.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete mongodb: {res}")

    spec = cfg.get("state.mongodb-operator.spec")
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete mongodb-operator: {res}")        
    return res

def delete(owner=None):
    if owner:       
        return delete_by_owner()
    else:
        return delete_by_spec()