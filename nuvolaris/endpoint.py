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

def create(owner=None):
    logging.info(f"*** Configuring http/s endpoint for openwhisk controller")

    #spec = kus.kustom_list("openwhisk-endpoint", [] , templates=[], data=None)
    #cfg.put("state.endpoint.spec", spec)
    spec = "deploy/openwhisk-endpoint"
    cfg.put("state.endpoint.spec", spec)        
    res = kube.kubectl("apply", "-f", spec)
    return res

    #if owner:
    #    kopf.append_owner_reference(spec['items'], owner)
    #else:
    #    cfg.put("state.endpoint.spec", spec)
    
    #return kube.apply(spec)

def delete():
    spec = cfg.get("state.endpoint.spec")
    res = False
    if spec:
        #res = kube.delete(spec)
        res = kube.kubectl("delete", "-f", spec)
        return res