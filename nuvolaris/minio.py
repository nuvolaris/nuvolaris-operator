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
import nuvolaris.util as util

def get_minio_standalone_pod_name():
    pod_name = kube.kubectl("get", "pods", jsonpath="{.items[?(@.metadata.labels.app == 'minio')].metadata.name}")
    if(pod_name):
        return pod_name[0]

    return None

def create(owner=None):
    logging.info(f"*** configuring minio standalone")

    data = {
        "minio_volume_size": cfg.get('minio.volume-size') or "5",
        "minio_root_user": cfg.get('minio.nuvolaris.root-user') or "minio",
        "minio_root_password": cfg.get('minio.nuvolaris.root-password') or "minio123",
        "storage_class": cfg.get("nuvolaris.storageClass")
    }
    
    kust = kus.patchTemplates("minio", ["00-minio-pvc.yaml","01-minio-dep.yaml"], data)    
    spec = kus.kustom_list("minio", kust, templates=[], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.minio.spec", spec)

    res = kube.apply(spec)

    pod_name = get_minio_standalone_pod_name()
    if pod_name:
        logging.info(f"checking for {pod_name}")
        while not kube.wait(f"pod/{pod_name}", "condition=ready"):
            logging.info(f"waiting for {pod_name} to be ready...")
            time.sleep(1)

    logging.info("*** configured minio standalone")
    return res

def delete():
    spec = cfg.get("state.minio.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete minio: {res}")
    return res

