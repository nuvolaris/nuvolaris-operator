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
import nuvolaris.openwhisk as openwhisk
import urllib.parse
import os, os.path
import logging, json
import kopf

from nuvolaris.user_config import UserConfig
from nuvolaris.user_metadata import UserMetadata


def _add_redis_user_metadata(ucfg: UserConfig, user_metadata:UserMetadata):
    """
    adds an entry for the redis connectivity, i.e
    something like "redis://{namespace}:{auth}@redis"}
    """ 

    try:
        redis_service =  util.get_service("{.items[?(@.spec.selector.name == 'redis')]}")
        if(redis_service):
            redis_service_name = redis_service['metadata']['name']
            redis_service_port = redis_service['spec']['ports'][0]['port']            
            username = urllib.parse.quote(ucfg.get('namespace'))
            password = urllib.parse.quote(ucfg.get('redis.password'))
            auth = f"{username}:{password}"
            redis_url = f"redis://{auth}@{redis_service_name}:{redis_service_port}"
            user_metadata.add_metadata("REDIS_URL",redis_url)            
        return None
    except Exception as e:
        logging.error(f"failed to build redis_url for {ucfg.get('namespace')}: {e}")
        return None 

def create(owner=None):
    logging.info("create redis")
    runtime = cfg.get('nuvolaris.kube')
    data = util.get_redis_config_data()
    
    tplp = ["set-attach.yaml"]

    if runtime == "openshift":
        tplp.append("security-set-attach.yaml")

    kust = kus.patchTemplates("redis",tplp , data)
    
    spec = kus.kustom_list("redis", kust, templates=["redis-conf.yaml"], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.redis.spec", spec)
    res = kube.apply(spec)

    wait_for_redis_ready()
    create_nuvolaris_db_user(data)

    logging.info(f"create redis: {res}")
    return res

def wait_for_redis_ready():
    # dynamically detect redis pod and wait for readiness
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.name == 'redis')].metadata.name}")

def create_nuvolaris_db_user(data):
    logging.info(f"authorizing redis for namespace nuvolaris")
    try:        
        data['mode']="create"
        path_to_script = render_redis_script(data['namespace'],"redis_manage_user_tpl.txt",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.name == 'redis')].metadata.name}")

        if(pod_name):
            res = exec_redis_command(pod_name,path_to_script)

            if(res):
                redis_service =  util.get_service("{.items[?(@.spec.selector.name == 'redis')]}")
                if(redis_service):
                    redis_service_name = redis_service['metadata']['name']
                    redis_service_port = redis_service['spec']['ports'][0]['port']
                    username = urllib.parse.quote(data['namespace'])
                    password = urllib.parse.quote(data['password'])
                    auth = f"{username}:{password}"
                    redis_url = f"redis://{auth}@{redis_service_name}:{redis_service_port}"
                    openwhisk.annotate(f"redis_url={redis_url}")
                    openwhisk.annotate(f"redis_prefix={data['prefix']}")
                    logging.info("*** saved annotation for redis nuvolaris user")
            return res

        return None
    except Exception as e:
        logging.error(f"failed to add redis namespace {data['namespace']}: {e}")
        return None   

def delete_by_owner():
    spec = kus.build("redis")
    res = kube.delete(spec)
    logging.info(f"delete redis: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.redis.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete redis: {res}")
    return res

def delete(owner=None):
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()    

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

def create_db_user(ucfg: UserConfig, user_metadata: UserMetadata):
    logging.info(f"authorizing new redis namespace {ucfg.get('namespace')}")    
    try:
        wait_for_redis_ready()
        data = util.get_redis_config_data()

        # if prefix not provided defaults to user namespace
        prefix = ucfg.get('redis.prefix') or ucfg.get('namespace') 
        if(not prefix.endswith(":")):
            prefix = f"{prefix}:"
        data['prefix']=prefix
        data['namespace']=ucfg.get('namespace')
        data['password']=ucfg.get('redis.password')        
        data['mode']="create"

        path_to_script = render_redis_script(ucfg.get('namespace'),"redis_manage_user_tpl.txt",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.name == 'redis')].metadata.name}")

        if(pod_name):
            res = exec_redis_command(pod_name,path_to_script)

            if res:
                user_metadata.add_metadata("REDIS_PREFIX",prefix)
                _add_redis_user_metadata(ucfg, user_metadata)
                return res
            else:
                logging.error(f"failed to add redis namespace {ucfg.get('namespace')}")

        return None
    except Exception as e:
        logging.error(f"failed to add redis namespace {ucfg.get('namespace')}: {e}")
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

def patch(status, action, owner=None):
    """
    Called the the operator patcher to create/delete redis
    """
    try:
        logging.info(f"*** handling request to {action} redis")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['redis']='on'
        else:
            msg = delete(owner)
            status['whisk_create']['redis']='off'

        logging.info(msg)        
        logging.info(f"*** hanlded request to {action} redis") 
    except Exception as e:
        logging.error('*** failed to update redis: %s' % e)
        status['whisk_create']['redis']='error'             

