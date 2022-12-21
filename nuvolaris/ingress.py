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

def get_ingress_yaml():
    runtime = cfg.get('nuvolaris.kube')
    return runtime == "eks" and "eks-nginx-ingress" or "generic-nginx-ingress"

def create(owner=None):
    ingress = kube.get("service/ingress-nginx-controller","ingress-nginx")
    if ingress:
        return "nginx-ingress already installed...skipping setup"
    else:
        ingress_yaml = get_ingress_yaml()
        logging.info(f"*** Configuring nginx-ingress {ingress_yaml}")
        # we apply the ingress specs as they are
        spec = kus.raw("nginx-ingress",ingress_yaml)
        cfg.put("state.ingress.spec", spec)        
        res = kube.kubectl("apply", "-f", f"deploy/nginx-ingress/{ingress_yaml}",namespace=None)
        return res

def delete():
    spec = cfg.get("state.ingress.spec")
    res = False
    ingress_yaml = get_ingress_yaml()
    if spec:
        res = kube.kubectl("delete", "-f", f"deploy/nginx-ingress/{ingress_yaml}",namespace=None)
        return res