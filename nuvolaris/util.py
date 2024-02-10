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
                        logging.warn(f"#{retry_number} nuv_retry detected a failure...")
                        continue  # retry again
                    else:
                        raise
        return wrapper

    return decorator


def get_default_storage_class():
    """
    Get the storage class attempting to get the default storage class defined on the configured kubernetes environment
    """
    storage_class = kube.kubectl("get", "storageclass", jsonpath="{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io\/is-default-class=='true')].metadata.name}")
    storage_class += kube.kubectl("get", "storageclass", jsonpath="{.items[?(@.metadata.annotations.storageclass\.beta\.kubernetes\.io\/is-default-class=='true')].metadata.name}")
    if(storage_class):
        return storage_class[0]

    return ""

def get_default_storage_provisioner():
    """
    Get the storage provisioner
    """    
    provisioner = kube.kubectl("get", "storageclass", jsonpath="{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io\/is-default-class=='true')].provisioner}")
    provisioner += kube.kubectl("get", "storageclass", jsonpath="{.items[?(@.metadata.annotations.storageclass\.beta\.kubernetes\.io\/is-default-class=='true')].metadata.name}")
    if(provisioner):
        return provisioner[0]

    return ""

def get_ingress_namespace(runtime):
    """
    Attempt to determine the namespace where the ingress-nginx-controller service has been deployed 
    checking the nuvolaris.ingresslb 
    - When set to 'auto' it will attempt to calculate it according to the kubernetes runtime
    - When set to <> 'auto' it will return the configured value. The configured value should be in the form <namespace>/<ingress-nginx-controller-service-name>
    >>> import nuvolaris.config as cfg
    >>> cfg.put('nuvolaris.ingresslb','auto')
    True
    >>> get_ingress_namespace('microk8s')
    'ingress'
    >>> get_ingress_namespace('kind')
    'ingress-nginx'
    >>> cfg.put('nuvolaris.ingresslb','ingress-nginx-azure/ingress-nginx-controller')
    True
    >>> get_ingress_namespace('kind')
    'ingress-nginx-azure'
    """        
    ingresslb_value = cfg.get('nuvolaris.ingresslb') or 'auto'

    if 'auto' != ingresslb_value:        
        ingress_namespace = ingresslb_value.split('/')[0]
        logging.debug(f"skipping ingress namespace auto detection and returning {ingress_namespace}")
        return ingress_namespace

    if runtime == "microk8s":
        return "ingress" 
    else:
        return  "ingress-nginx"

def get_ingress_service_name(runtime):
    """
    Attempt to determine the namespace where the ingress-nginx-controller service has been deployed 
    checking the nuvolaris.ingresslb 
    - When set to 'auto' it will attempt to calculate it according to the kubernetes runtime
    - When set to <> 'auto' it will return the configured value. The configured value should be in the form <namespace>/<ingress-nginx-controller-service-name>
    >>> import nuvolaris.config as cfg
    >>> cfg.put('nuvolaris.ingresslb','auto')
    True
    >>> get_ingress_service_name('microk8s')
    'service/ingress-nginx-controller'
    >>> get_ingress_service_name('kind')
    'service/ingress-nginx-controller'
    >>> cfg.put('nuvolaris.ingresslb','ingress-nginx-azure/ingress-nginx-controller-custom')
    True
    >>> get_ingress_service_name('kind')
    'service/ingress-nginx-controller-custom'
    """        
    ingresslb_value = cfg.get('nuvolaris.ingresslb') or 'auto'

    if 'auto' != ingresslb_value:
        ingress_srv_name = f"service/{ingresslb_value.split('/')[1]}"
        logging.debug(f"skipping ingress service name auto detection and returning {ingress_srv_name}")
        return ingress_srv_name
   
    return "service/ingress-nginx-controller"

def get_ingress_class(runtime):
    """
    Attempt to determine the proper ingress class
    - When set to 'auto' it will attempt to calculate it according to the kubernetes runtime
    - When set to <> 'auto' it will return the configured value.
    """      
    ingress_class = cfg.get('nuvolaris.ingressclass') or 'auto'

    if 'auto' != ingress_class:
        logging.warn(f"skipping ingress class auto detection and returning {ingress_class}")
        return ingress_class

    # ingress class default to nginx
    ingress_class = "nginx"

    # On microk8s ingress class must be public
    if runtime == "microk8s":
        ingress_class = "public"

    # On k3s ingress class must be traefik
    if runtime == "k3s":
        ingress_class = "traefik" 
    
    return ingress_class  

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
        'mongo_nuvolaris_password': cfg.get('mongodb.nuvolaris.password') or "s0meP@ass3",
        'size': cfg.get('mongodb.volume-size') or 10,
        'pvcName': 'mongodb-data',
        'storageClass':cfg.get("nuvolaris.storageclass"),
        'pvcAccessMode':'ReadWriteOnce'    
        }
    return data

def parse_image(img):
    """
    Parse a string representing a pod image in the form <image>:<tag> and return
    a dictionary containing {"image":<img>, "tag":<tag>}
    >>> img_data = parse_image("ghcr.io/nuvolaris/openwhisk-controller:0.3.0-morpheus.22122609")
    >>> "ghcr.io/nuvolaris/openwhisk-controller" == img_data["image"]
    True
    >>> "0.3.0-morpheus.22122609" == img_data["tag"]
    True
    """
    tmp_img_items = img.split(":")

    if len(tmp_img_items) != 2:
        raise Exception(f"wrong image name format {img}. Image and tag must be separated by a :")

    data = {
        "image": tmp_img_items[0],
        "tag": tmp_img_items[1],
    }

    return data

def get_controller_image_data(data):
    controller_image = cfg.get("controller.image")

    if ":" in controller_image:
        img_data = parse_image(controller_image)
        data['controller_image'] = img_data["image"]
        data['controller_tag'] = img_data["tag"]
    else:        
        data['controller_image'] = cfg.get("controller.image") or "ghcr.io/nuvolaris/openwhisk-controller"
        data['controller_tag'] = cfg.get("controller.tag") or "3.1.0-mastrogpt.2402101445"

# return configuration parameters for the standalone controller
def get_standalone_config_data():        
    data = {
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
        "activation_payload_max": cfg.get('configs.limits.activations.max_allowed_payload') or "1048576",
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
        "invoker_containerpool_usermemory": cfg.get('configs.invoker.containerPool.userMemory') or "2048m",
        "container_cpu_req": cfg.get('configs.controller.resources.cpu-req') or "500m",
        "container_cpu_lim": cfg.get('configs.controller.resources.cpu-lim') or "1",
        "container_mem_req": cfg.get('configs.controller.resources.mem-req') or "1G",
        "container_mem_lim": cfg.get('configs.controller.resources.mem-lim') or "2G",
        "container_manage_resources": cfg.exists('configs.controller.resources.cpu-req')
    }

    get_controller_image_data(data)
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

# return redis configuration parameters with default values if not configured
def get_redis_config_data():
    # ensure prefix key contains : at the end to be compliant with REDIS script ACL creator
    prefix = cfg.get("redis.nuvolaris.prefix") or "nuvolaris:"

    if(not prefix.endswith(":")):
        prefix = f"{prefix}:"

    data = {
        "applypodsecurity":get_enable_pod_security(),
        "name": "redis",
        "container": "redis",
        "dir": "/bitnami/redis/data",
        "size": cfg.get("redis.volume-size", "REDIS_VOLUME_SIZE", 10),
        "storageClass": cfg.get("nuvolaris.storageclass"),
        "redis_password":cfg.get("redis.default.password") or "s0meP@ass3",
        "namespace":"nuvolaris",
        "password":cfg.get("redis.nuvolaris.password") or "s0meP@ass3",
        "prefix": prefix,
        "persistence": cfg.get("redis.persistence-enabled") or False,
        "maxmemory": cfg.get("redis.maxmemory") or "1000mb"
    }
    return data

def get_service(jsonpath,namespace="nuvolaris"):
    services= kube.kubectl("get", "svc", namespace=namespace, jsonpath=jsonpath)
    if(services):
        return services[0]

    raise Exception(f"could not find any svc matching jsonpath={jsonpath}")

# return minio configuration parameters with default values if not configured
def get_minio_config_data():
    data = {
        "applypodsecurity":get_enable_pod_security(),
        "name":"minio-deployment",
        "container":"minio",
        "minio_host": cfg.get('minio.host') or "minio",
        "minio_volume_size": cfg.get('minio.volume-size') or "5",
        "minio_root_user": cfg.get('minio.admin.user') or "minio",
        "minio_root_password": cfg.get('minio.admin.password') or "minio123",
        "storage_class": cfg.get("nuvolaris.storageclass"),
        "minio_nuv_user": cfg.get('minio.nuvolaris.user') or "nuvolaris",
        "minio_nuv_password": cfg.get('minio.nuvolaris.password') or "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
    }
    return data

# return postgres configuration parameter with default valued if not configured
def get_postgres_config_data():
    data = {
        'postgres_root_password': cfg.get('postgres.admin.password') or "0therPa55",
        'postgres_root_replica_password': cfg.get('postgres.admin.password') or "0therPa55sd",
        'postgres_nuvolaris_user': "nuvolaris",
        'postgres_nuvolaris_password': cfg.get('postgres.nuvolaris.password') or "s0meP@ass3",
        'size': cfg.get('postgres.volume-size') or 10,
        'replicas': cfg.get('postgres.admin.replicas') or 2,
        'storageClass': cfg.get('nuvolaris.storageclass')
        }
    return data

# wait for a service matching the given jsonpath name
@nuv_retry()
def wait_for_service(jsonpath,namespace="nuvolaris"):
    service_names = kube.kubectl("get", "svc", namespace=namespace, jsonpath=jsonpath)
    if(service_names):
        return service_names[0]

    raise Exception(f"could not find any pod matching jsonpath={jsonpath}")

def get_controller_http_timeout():    
    return cfg.get("configs.limits.time.limit-max") or "5min"

def get_apihost_from_config_map(namespace="nuvolaris"):
    annotations= kube.kubectl("get", "cm/config", namespace=namespace, jsonpath='{.metadata.annotations.apihost}')
    if(annotations):
        return annotations[0]

    raise Exception("Could not find apihost annotation inside internal cm/config config Map")  

def get_value_from_config_map(namespace="nuvolaris", path='{.metadata.annotations.apihost}'):
    annotations= kube.kubectl("get", "cm/config", namespace=namespace, jsonpath=path)
    if(annotations):
        return annotations[0]

    raise Exception(f"Could not find {path} annotation inside internal cm/config config Map")

def get_enable_pod_security():
    """
    Return true if there is the need to enable pod security context
    for some specific pod. This is a test based on some empiric assumption on runtime 
    basis and/or storage class.
    @TODO: find a better way to determine when this function should return true.
    """
    runtime = cfg.get('nuvolaris.kube')    
    storage_class = cfg.get('nuvolaris.storageclass')    
    return runtime in ["eks","gke","aks","generic"] or (runtime in ["k3s"] and "rook" in storage_class)
    

def get_runtimes_json_from_config_map(namespace="nuvolaris", path='{.data.runtimes\.json}'):
    """ Return the configured runtimes.json from the config map cm/openwhisk-runtimes
    """
    runtimes= kube.kubectl("get", "cm/openwhisk-runtimes", namespace=namespace, jsonpath=path)
    if(runtimes):
        return runtimes[0]

    raise Exception("Could not find runtimes.json inside cm/openwhisk-runtimes config Map")