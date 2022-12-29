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
    logging.info(f"*** Configuring cluster issuer")
    # We deploy a cluster-issuer
    runtime = cfg.get('nuvolaris.kube')
    acme_registered_email = cfg.get('tls.acme-registered-email') or "nuvolaris@nuvolaris.io"
    acme_server_url = cfg.get('tls.acme-server-url') or "https://acme-staging-v02.api.letsencrypt.org/directory"

    # On microk8s cluster issuer class must be public
    issuer_class = runtime == "microk8s" and "public" or "nginx"
    
    logging.info(f"*** Configuring cluster issuer using email {acme_registered_email}")
    logging.info(f"*** Configuring cluster issuer using let's encrypt server {acme_server_url}")
  
    data = {
        "acme_registered_email": acme_registered_email,
        "acme_server_url": acme_server_url,
        "issuer_class":issuer_class,
        "name": "tls"
    }
    
    kust = kus.patchTemplate("issuer", "cluster-issuer.yaml", data)
    spec = "deploy/issuer/__cluster-issuer.yaml"

    cfg.put("state.issuer.spec", spec)
    res = kube.kubectl("apply", "-f", spec,namespace=None)
    return res

def delete():
    spec = cfg.get("state.issuer.spec")
    res = False
    if spec:
        res = kube.kubectl("delete", "-f", spec,namespace=None)
        return res

