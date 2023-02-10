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
# this module wraps utilities functions
import nuvolaris.kube as kube
import logging
import time, random, math
import nuvolaris.config as cfg

# Implements truncated exponential backoff from
# https://cloud.google.com/storage/docs/retry-strategy#exponential-backoff
def nuv_retry(deadline_seconds=120, max_backoff=5):
    def decorator(function):
        from functools import wraps

        @wraps(function)
        def wrapper(*args, **kwargs):
            deadline = time.time() + deadline_seconds
            retry_number = 0

            while True:
                try:
                    result = function(*args, **kwargs)
                    return result
                except Exception as e:
                    current_t = time.time()
                    backoff_delay = min(
                            math.pow(2, retry_number) + random.random(), max_backoff
                    )
                    
                    if current_t + backoff_delay < deadline:
                        time.sleep(backoff_delay)
                        retry_number += 1
                        continue  # retry again
                    else:
                        raise
        return wrapper

    return decorator


# get the default storage class defined on the configured kubernetes environment
def get_default_storage_class():
    storage_class = kube.kubectl("get", "storageclass", jsonpath="{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io\/is-default-class)].metadata.name}")
    if(storage_class):
        return storage_class[0]

    return ""

# get the default storage provisioner defined on the configured kubernetes environment
def get_default_storage_provisioner():
    provisioner = kube.kubectl("get", "storageclass", jsonpath="{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io\/is-default-class)].provisioner}")
    if(provisioner):
        return provisioner[0]

    return ""

# determine the ingress-nginx flavour
def get_ingress_namespace(runtime):
    if runtime == "microk8s":
        return "ingress" 
    else:
        return  "ingress-nginx"

# determine the ingress-nginx flavour
def get_ingress_yaml(runtime):
    if runtime == "eks":
        return "eks-nginx-ingress.yaml"
    elif runtime == "kind":
        return  "kind-nginx-ingress.yaml"  
    else:
        return  "cloud-nginx-ingress.yaml"

# wait for a pod name
@nuv_retry()
def get_pod_name(jsonpath,namespace="nuvolaris"):
    pod_name = kube.kubectl("get", "pods", namespace=namespace, jsonpath=jsonpath)
    if(pod_name):
        return pod_name[0]

    raise Exception(f"could not find any pod matching jsonpath={jsonpath}")        

# helper method waiting for a pod ready using the given jsonpath to retrieve the pod name
def wait_for_pod_ready(pod_name_jsonpath, timeout="600s", namespace="nuvolaris"):
    try:        
        pod_name = get_pod_name(pod_name_jsonpath, namespace)
        logging.info(f"checking pod {pod_name}")        
        while not kube.wait(f"pod/{pod_name}", "condition=ready", timeout, namespace):
            logging.info(f"waiting for {pod_name} to be ready...")
            time.sleep(1)
    except Exception as e:
        logging.error(e)

# return mongodb configuration parameter with default valued if not configured
def get_mongodb_config_data():
    data = {
        'mongo_admin_user': cfg.get('mongodb.admin.user') or "whisk_user",
        'mongo_admin_password': cfg.get('mongodb.admin.password') or "0therPa55",
        'mongo_nuvolaris_user': cfg.get('mongodb.nuvolaris.user') or "nuvolaris",
        'mongo_nuvolaris_password': cfg.get('mongodb.nuvolaris.password') or "s0meP@ass3"
    }
    return data        
    