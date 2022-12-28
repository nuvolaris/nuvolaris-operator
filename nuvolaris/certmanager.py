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
        spec = "deploy/cert-manager/cert-manager.yaml"
        cfg.put("state.cm.spec", spec)       
        res = kube.kubectl("apply", "-f", spec, namespace=None)
        return res

def delete():
    spec = cfg.get("state.cm.spec")
    res = False
    if spec:
        res = kube.kubectl("delete", "-f", spec, namespace=None)
        return res