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
#
# Deploys mongodb for nuvolaris using operator or standalone
# implementation.
#
# By default standalone configuration is used unless mongodb.useOperator is set to true
#
import nuvolaris.config as cfg
import nuvolaris.util as util
import nuvolaris.mongodb_operator as operator
import nuvolaris.mongodb_standalone as standalone
import nuvolaris.kube as kube
import nuvolaris.template as ntp
import logging, json
import os
import urllib.parse
import nuvolaris.openwhisk as openwhisk

from nuvolaris.user_config import UserConfig
from nuvolaris.user_metadata import UserMetadata

def get_mdb_pod_name():
    useOperator = cfg.get('mongodb.useOperator') or False
    pod_name_jsonpath = useOperator and "{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb-svc')].metadata.name}" or "{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb')].metadata.name}"
    return util.get_pod_name(pod_name_jsonpath)

def _add_mdb_user_metadata(ucfg, user_metadata):
    """
    adds an entry for the mongodb connectivity, i.e
    something like "mongodb://{namespace}:{auth}@nuvolaris-mongodb-0.nuvolaris-mongodb-svc.nuvolaris.svc.cluster.local:27017/{database}?connectTimeoutMS=60000"}
    """ 

    try:
        mdb_service = util.get_service("{.items[?(@.metadata.name == 'nuvolaris-mongodb-svc')]}")

        if(mdb_service):
            mdb_service_name = mdb_service['metadata']['name']            
            mdb_ns = mdb_service['metadata']['namespace']
            mdb_pod_name = get_mdb_pod_name()
            
            username = urllib.parse.quote(ucfg.get('namespace'))
            password = urllib.parse.quote(ucfg.get('mongodb.password'))
            auth = f"{username}:{password}"
            database = ucfg.get('mongodb.database')

            mdb_url = f"mongodb://{auth}@{mdb_pod_name}.{mdb_service_name}.{mdb_ns}.svc.cluster.local:27017/{database}?connectTimeoutMS=60000"
            user_metadata.add_metadata("MONGODB_URL",mdb_url)
        return None
    except Exception as e:
        logging.error(f"failed to build mongodb_url for {ucfg.get('mongodb.database')}: {e}")
        return None  

def create(owner=None):
    """
    Deploys the mongodb operator and wait for the operator to be ready.
    """
    useOperator = cfg.get('mongodb.useOperator') or False

    res = useOperator and operator.create(owner) or standalone.create(owner)

    if(res):
        update_system_cm_for_mdb()

    return res

def update_system_cm_for_mdb():
    logging.info("*** annotating configuration for mongodb nuvolaris user")
    try:        
        mdb_service = util.get_service("{.items[?(@.metadata.name == 'nuvolaris-mongodb-svc')]}")
        if(mdb_service):
            mdb_pod_name = get_mdb_pod_name()                
            mdb_service_name = mdb_service['metadata']['name']            
            mdb_ns = mdb_service['metadata']['namespace']

            data = util.get_mongodb_config_data()

            username = urllib.parse.quote(data['mongo_nuvolaris_user'])
            password = urllib.parse.quote(data['mongo_nuvolaris_password'])
            auth = f"{username}:{password}"
            
            mdb_url = f"mongodb://{auth}@{mdb_pod_name}.{mdb_service_name}.{mdb_ns}.svc.cluster.local:27017/nuvolaris?connectTimeoutMS=60000"
            openwhisk.annotate(f"mongodb_url={mdb_url}")
            logging.info("*** saved annotation for mongodb nuvolaris user")            
    except Exception as e:
        logging.error(f"failed to build mongodb_url for nuvolaris database: {e}")    

def delete(owner=None):
    useOperator = cfg.get('mongodb.useOperator') or False

    if useOperator:
        return operator.delete(owner)

    return standalone.delete(owner)    

def init():
    return "TODO"

def render_mongodb_script(namespace,template,data):
    """
    uses the given template to render a js script to execute as a json.
    """  
    out = f"/tmp/__{namespace}_{template}"
    file = ntp.spool_template(template, out, data)
    return os.path.abspath(file)

def exec_mongosh_command(pod_name,path_to_mdb_script):
    logging.info(f"passing script {path_to_mdb_script} to pod {pod_name}")
    res = kube.kubectl("cp",path_to_mdb_script,f"{pod_name}:{path_to_mdb_script}")
    res = kube.kubectl("exec","-it",pod_name,"--","/bin/bash","-c",f"mongosh --file {path_to_mdb_script}")
    os.remove(path_to_mdb_script)
    return res

def create_db_user(ucfg: UserConfig, user_metadata: UserMetadata):
    database = ucfg.get('mongodb.database')
    logging.info(f"authorizing new mongodb database {database}")

    try:
        data = util.get_mongodb_config_data()
        data["database"]=database
        data["subject"]=ucfg.get('namespace')
        data["auth"]=ucfg.get('mongodb.password')
        data["mode"]="create"

        path_to_mdb_script = render_mongodb_script(ucfg.get('namespace'),"mongodb_manage_user_tpl.js",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb')].metadata.name}")

        if(pod_name):
            res = exec_mongosh_command(pod_name,path_to_mdb_script)
            _add_mdb_user_metadata(ucfg, user_metadata)
            return res

        return None
    except Exception as e:
        logging.error(f"failed to add Mongodb database {database}: {e}")
        return None

def delete_db_user(namespace, database):
    logging.info(f"removing mongodb database {database}")

    try:
        data = util.get_mongodb_config_data()
        data["subject"]=namespace
        data["database"]=database
        data["mode"]="delete"

        path_to_mdb_script = render_mongodb_script(namespace,"mongodb_manage_user_tpl.js",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb')].metadata.name}")

        if(pod_name):
            res = exec_mongosh_command(pod_name,path_to_mdb_script)
            return res

        return None
    except Exception as e:
        logging.error(f"failed to remove Mongodb database {namespace} authorization id and key: {e}")
        return None

def patch(status, action, owner=None):
    """
    Called the the operator patcher to create/delete mongodb
    """
    try:
        logging.info(f"*** handling request to {action} mongodb")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['mongodb']='on'
        else:
            msg = delete(owner)
            status['whisk_create']['mongodb']='off'

        logging.info(msg)        
        logging.info(f"*** hanlded request to {action} mongodb") 
    except Exception as e:
        logging.error('*** failed to update mongodb: %s' % e)
        status['whisk_create']['mongodb']='error'                 