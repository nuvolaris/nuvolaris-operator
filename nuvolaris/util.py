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
import time, random, math, os
import nuvolaris.config as cfg
import uuid

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

# return configuration parameters for the standalone controller
def get_standalone_config_data():
    data = {
        "controller_image": cfg.get("controller.image") or  "ghcr.io/nuvolaris/openwhisk-controller",
        "controller_tag": cfg.get("controller.tag") or "0.3.0-morpheus.22122609",
        "couchdb_host": cfg.get("couchdb.host") or "couchdb",
        "couchdb_port": cfg.get("couchdb.port") or "5984",
        "couchdb_admin_user": cfg.get("couchdb.admin.user"),
        "couchdb_admin_password": cfg.get("couchdb.admin.password"),
        "couchdb_controller_user": cfg.get("couchdb.controller.user"),
        "couchdb_controller_password": cfg.get("couchdb.controller.password"),
        "triggers_fires_perMinute": cfg.get("configs.limits.triggers.fires-perMinute") or 60,
        "actions_sequence_maxLength": cfg.get("configs.limits.actions.sequence-maxLength") or 50,
        "actions_invokes_perMinute": cfg.get("configs.limits.actions.invokes-perMinute") or 60,
        "actions_invokes_concurrent": cfg.get("configs.limits.actions.invokes-concurrent") or 30,
        "time_limit_min": cfg.get("configs.limits.time.limit-min") or "100ms", 
        "time_limit_std": cfg.get("configs.limits.time.limit-std") or "1min", 
        "time_limit_max": cfg.get("configs.limits.time.limit-max") or "5min", 
        "memory_limit_min": cfg.get("configs.limits.memory.limit-min") or "128m", 
        "memory_limit_std": cfg.get("configs.limits.memory.limit-std") or "256m", 
        "memory_limit_max": cfg.get("configs.limits.memory.limit-max") or "512m", 
        "concurrency_limit_min": cfg.get("configs.limits.concurrency.limit-min") or 1, 
        "concurrency_limit_std": cfg.get("configs.limits.concurrency.limit-std") or 1, 
        "concurrency_limit_max": cfg.get("configs.limits.concurrency.limit-max") or 1,
        "controller_java_opts": cfg.get('configs.controller.javaOpts') or "-Xmx2048M",
    }
    return data

def validate_ow_auth(auth):
    """
        >>> import nuvolaris.testutil as tutil
        >>> import nuvolaris.util as util
        >>> auth = tutil.generate_ow_auth()
        >>> util.validate_ow_auth(auth)
        True
        >>> util.validate_ow_auth('21321:3213216')
        False
    """ 
    try:
        parts = auth.split(':')
        try:
            uid = str(uuid.UUID(parts[0], version = 4))
        except ValueError:
            logging.error('authorization id is not a valid UUID')
            return False

        key = parts[1]
        if len(key) < 64:
            logging.error('authorization key must be at least 64 characters long')
            return False
        
        return True
    except Exception as e:
        logging.error('failed to determine authorization id and key: %s' % e)
        return False

def check(f, what, res):
    if f:
        logging.info(f"OK: {what}")
        return res and True
    else:
        logging.warn(f"ERR: {what}")
        return False

# return redis configuration parameter with default valued if not configured
def get_redis_config_data():
    data = {
        "name": "redis",
        "dir": "/redis-master-data",
        "size": cfg.get("couchdb.volume-size", "REDIS_VOLUME_SIZE", 10),
        "storageClass": cfg.get("nuvolaris.storageClass"),
        "redis_password":cfg.get("redis.default.password") or "s0meP@ass3"
    }
    return data

def get_service(jsonpath,namespace="nuvolaris"):
    services= kube.kubectl("get", "svc", namespace=namespace, jsonpath=jsonpath)
    if(services):
        return services[0]

    raise Exception(f"could not find any svc matching jsonpath={jsonpath}")                                