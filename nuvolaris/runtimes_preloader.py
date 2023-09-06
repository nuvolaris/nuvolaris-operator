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
import kopf, logging
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.util as util
import nuvolaris.runtimes_util as rutil
import json

def create(owner=None):
    logging.info(f"*** configuring runtime preloader")

    runtimes_as_json = util.get_runtimes_json_from_config_map()
    data=rutil.parse_runtimes(json.loads(runtimes_as_json))

    kust = kus.patchTemplates("runtimes", ["runtimes-job-container-attach.yaml"], data)
    spec = kus.kustom_list("runtimes", kust, templates=[], data=data)
    
    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.preloader.spec", spec)

    res = kube.apply(spec)

    logging.info("*** configured runtime preloader")
    return res



def delete_by_owner():
    spec = kus.build("runtimes")
    res = kube.delete(spec)
    logging.info(f"delete runtimes preloader: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.preloader.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete runtimes preloader: {res}")
    return res

def delete(owner=None):
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()