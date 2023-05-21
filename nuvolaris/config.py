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
import flatdict, json, os
import logging

_config = {}

# define a configuration 
# the configuration is a map, followed by a list of labels 
# the map can be a serialized json and will be flattened to a map of values.
# you can have only a configuration active at a time
# if you want to set a new configuration you have to clean it
def configure(spec: dict):
    global _config
    _config = dict(flatdict.FlatDict(spec, delimiter="."))
    return True

def clean():
    global _config
    _config = {}

def exists(key):
    return key in _config

def get(key, envvar=None, defval=None):
    val = _config.get(key)

    if envvar and envvar in os.environ:
        val = os.environ[envvar]
    
    if val: 
        return val
    
    return defval

def put(key, value):
    _config[key] = value
    return True

def delete(key):
    if key in _config:
        del _config[key]
        return True

def getall(prefix=""):
    res = {}
    for key in _config.keys():
        if key.startswith(prefix):
            res[key] = _config[key]
    return res

def keys(prefix=""):
    res = []
    if _config:
        for key in _config.keys():
            if key.startswith(prefix):
                res.append(key)
    return res

def detect_labels(labels=None):
    # read labels if not avaibale
    if not labels:
        import nuvolaris.kube as kube
        labels = kube.kubectl("get", "nodes", jsonpath='{.items[].metadata.labels}')
    
    res = {}
    kube = None
    for i in labels:
        for j in list(i.keys()):
            if j.startswith("nuvolaris.io/"):
                key = f"nuvolaris.{j[13:]}"
                res[key] = i[j]
                _config[key] = i[j]

    for i in labels:
        for j in list(i.keys()):
            # detect the kube type
            if j.find("eksctl.io") >= 0:
                kube ="eks"
                break
            if j.find("k8s.io/cloud-provider-aws"):
                kube ="eks"
                break
            elif j.find("microk8s.io") >= 0:
                kube = "microk8s"
                break
            elif j.find("lke.linode.com") >=0:
                kube = "lks"
                break
            elif j.find("node.openshift.io") >=0:
                kube = "openshift"
                break
            #elif j.endswith("kubernetes.io/instance-type"): 
            #    kube = i[j]               
            # assign all the 'nuvolaris.io' labels
        
    if kube:
        res["nuvolaris.kube"] = kube 
        _config["nuvolaris.kube"] = kube

    if not "nuvolaris.kube" in _config:
        _config["nuvolaris.kube"] = "generic"
        res["nuvolaris.kube"] = "generic"

    return res

def detect_storage(storages=None):
    res = {}
    if not storages:
        import nuvolaris.util as util

        try:
            storage_class = util.get_default_storage_class()
            provisioner = util.get_default_storage_provisioner()

            if(storage_class):
                res['nuvolaris.storageClass'] = storage_class
                _config['nuvolaris.storageClass'] = storage_class
                res['nuvolaris.provisioner'] = provisioner
                _config['nuvolaris.provisioner'] = provisioner
        except:
            pass
    return res

def detect_env():
    _config['operator.image'] = os.environ.get("OPERATOR_IMAGE", "missing-OPERATOR_IMAGE")
    _config['operator.tag'] = os.environ.get("OPERATOR_TAG", "missing-OPERATOR_TAG")
    _config['controller.image'] = os.environ.get("CONTROLLER_IMAGE", "missing-CONTROLLER_IMAGE")
    _config['controller.tag'] = os.environ.get("CONTROLLER_TAG", "missing-CONTROLLER_TAG")
    _config['invoker.image'] = os.environ.get("INVOKER_IMAGE", "missing-INVOKER_IMAGE")
    _config['invoker.tag'] = os.environ.get("INVOKER_TAG", "missing-INVOKER_TAG")

def detect():
    detect_storage()
    detect_labels()
    detect_env()

def detect_ingress_class():
    runtime = _config['nuvolaris.kube']

    # ingress class default to nginx
    ingress_class = "nginx"

    # On microk8s ingress class must be public
    if runtime == "microk8s":
        ingress_class = "public"

    # On k3s ingress class must be traefik
    if runtime == "k3s":
        ingress_class = "traefik" 
    
    return ingress_class

def dump_config():
    import nuvolaris.config as cfg
    for k in cfg.getall():
        logging.debug(f"{k} = {cfg.get(k)}") 
