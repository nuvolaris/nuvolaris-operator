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
import kopf, logging, json
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg

def create(owner=None):
    logging.info(f"*** Configuring certificate manager")
    
    cm = kube.get("service/cert-manager","cert-manager")
    if cm:
        return "certificate manager is already installed...skipping setup"
    else:
        # we apply the cert-manager.yaml as is
        spec = kus.raw("cert-manager","cert-manager.yaml")
        cfg.put("state.cm.spec", spec)        
        res = kube.kubectl("apply", "-f", "deploy/cert-manager/cert-manager.yaml",namespace=None)
        return res
    
    # We deploy a cluster-issuer
    #acme_registered_email = cfg.get('tls.acme-registered-email') or "nuvolaris@nuvolaris.io"
    #acme_server_url = cfg.get('tls.acme-server-url') or "https://acme-staging-v02.api.letsencrypt.org/directory"
    
    #logging.info(f"*** Configuring cluster issuer using email {acme_registered_email}")
    #logging.info(f"*** Configuring cluster issuer using let's encrypt server {acme_server_url}")

    #config = json.dumps(cfg.getall())
    #data = {
    #    "acme_registered_email": acme_registered_email,
    #    "acme_server_url": acme_server_url,
    #    "name": "tls"
    #}
    
    #kus.patchTemplates("cert-manager", ["cluster-issuer.yaml"], data)
    #spec = kus.raw("cert-manager","__cluster-issuer.yaml")
    #cfg.put("state.issuer.spec", spec)
        
    # create a cluster issuer
    #res = kube.kubectl("apply", "-f", "deploy/cert-manager/__cluster-issuer.yaml",namespace=None)
    #return res

def delete():
    spec = cfg.get("state.cm.spec")
    res = False
    if spec:
        res = kube.kubectl("delete", "-f", "deploy/cert-manager/cert-manager.yaml",namespace=None)
        return res