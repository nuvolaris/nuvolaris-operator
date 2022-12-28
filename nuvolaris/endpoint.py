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
import kopf, logging, json, time
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import urllib.parse

def create(owner=None,url="http://localhost:3233"):
    runtime = cfg.get('nuvolaris.kube')
    tls = cfg.get('components.tls')
    url = urllib.parse.urlparse(url)
    hostname = url.hostname

    if(runtime == "kind" or not tls):
        logging.info(f"*** Configuring host {hostname} as http endpoint for openwhisk controller")
        spec = "deploy/openwhisk-endpoint/standalone-in-http.yaml"
        cfg.put("state.endpoint.spec", spec)
        cfg.put("state.endpoint.apply", "file")
        res = kube.kubectl("apply", "-f", spec)
        return res
    
    logging.info(f"*** Configuring host {hostname} as https endpoint for openwhisk controller")
    # On microk8s cluster issuer class must be public
    ingress_class = runtime == "microk8s" and "public" or "nginx"
    
    data = {
        "apihost":hostname,
        "ingress_class":ingress_class
    }
    ikust = kus.patchTemplates("openwhisk-endpoint", ["standalone-in-https.yaml"], data)
    ispec = kus.restricted_kustom_list("openwhisk-endpoint", ikust, templates=[],templates_filter=["standalone-in-https.yaml"],data=data)
     
    if owner:
            kopf.append_owner_reference(ispec['items'], owner)
    else:
        cfg.put("state.endpoint.spec", ispec)
        cfg.put("state.endpoint.apply", "spec")
        
    return kube.apply(ispec)

def delete():
    spec = cfg.get("state.endpoint.spec")
    apply = cfg.get("state.endpoint.apply")
    res = False
    if spec:
        if(apply == "file"):
            res = kube.kubectl("delete", "-f", spec)
            return res
        else:
            res = kube.delete(spec)
            return res
