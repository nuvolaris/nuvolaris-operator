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
import logging
import os

def create(owner=None):
    """
    Deploys the mongodb operator and wait for the operator to be ready.
    """
    useOperator = cfg.get('mongodb.useOperator') or False

    if useOperator:
        logging.info("*** creating mongodb using operator mode") 
        return operator.create(owner)

    logging.info("*** creating mongodb using standalone mode") 
    return standalone.create(owner)

def delete():
    useOperator = cfg.get('mongodb.useOperator') or False

    if useOperator:
        return operator.delete()

    return standalone.delete()    

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

def create_db_user(namespace, database, auth):
    logging.info(f"authorizing new mongodb database {database}")

    try:
        data = util.get_mongodb_config_data()
        data["subject"]=namespace
        data["database"]=database
        data["auth"]=auth
        data["mode"]="create"

        path_to_mdb_script = render_mongodb_script(namespace,"mongodb_manage_user_tpl.js",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb')].metadata.name}")

        if(pod_name):
            res = exec_mongosh_command(pod_name,path_to_mdb_script)
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