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

import nuvolaris.kustomize as kus
import nuvolaris.kube as kube
import nuvolaris.config as cfg
import nuvolaris.template as ntp
import nuvolaris.util as util
import urllib.parse
import os, os.path
import logging
import kopf

def create(owner=None):
    logging.info("create redis")
    data = util.get_redis_config_data()
    kust = kus.patchTemplate("redis", "set-attach.yaml", data)
    spec = kus.kustom_list("redis", kust, templates=["redis-conf.yaml"], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.redis.spec", spec)
    res = kube.apply(spec)

    wait_for_redis_ready()

    logging.info(f"create redis: {res}")
    return res

def wait_for_redis_ready():
    # dynamically detect redis pod and wait for readiness
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.name == 'redis')].metadata.name}")

def delete():
    spec = cfg.get("state.redis.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete redis: {res}")
    return res

def render_redis_script(namespace,template,data):
    """
    uses the given template to render a redis-cli script to be executed.
    """  
    out = f"/tmp/__{namespace}_{template}"
    file = ntp.spool_template(template, out, data)
    return os.path.abspath(file)

def exec_redis_command(pod_name,path_to_script):
    logging.info(f"passing script {path_to_script} to pod {pod_name}")
    res = kube.kubectl("cp",path_to_script,f"{pod_name}:{path_to_script}")
    res = kube.kubectl("exec","-it",pod_name,"--","/bin/bash","-c",f"cat {path_to_script} | redis-cli")
    os.remove(path_to_script)
    return res

def create_db_user(namespace,prefix,auth):
    logging.info(f"authorizing new redis namespace {namespace}")    
    try:
        wait_for_redis_ready()
        data = util.get_redis_config_data()
        data['namespace']=namespace
        data['password']=auth
        data['prefix']=prefix
        data['mode']="create"

        path_to_script = render_redis_script(namespace,"redis_manage_user_tpl.txt",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.name == 'redis')].metadata.name}")

        if(pod_name):
            res = exec_redis_command(pod_name,path_to_script)
            return res

        return None
    except Exception as e:
        logging.error(f"failed to add redis namespace {namespace}: {e}")
        return None

def delete_db_user(namespace):
    logging.info(f"removing redis namespace {namespace}")

    try:        
        data = util.get_redis_config_data()
        data["namespace"]=namespace
        data["mode"]="delete"

        path_to_script = render_redis_script(namespace,"redis_manage_user_tpl.txt",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.name == 'redis')].metadata.name}")

        if(pod_name):
            res = exec_redis_command(pod_name,path_to_script)
            return res

        return None
    except Exception as e:
        logging.error(f"failed to remove redis namespace {namespace}: {e}")
        return None     

