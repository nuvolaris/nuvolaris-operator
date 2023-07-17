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
# Deploys a standalone ferretdb relying on postgres db
#

import kopf, json, time
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.util as util
import nuvolaris.postgres_operator as postgres
import logging
import nuvolaris.openwhisk as openwhisk
import urllib.parse

from nuvolaris.user_config import UserConfig
from nuvolaris.user_metadata import UserMetadata

def create(owner=None):
    """
    Deploys ferret db and wait for the pod to be ready.
    """
    logging.info("*** creating ferretdb")

    data = util.get_postgres_config_data()
    # use nuvolari spostgresdb as default user
    data['ferretdb_postgres_url']=util.get_value_from_config_map(path='{.metadata.annotations.postgres_url}')

    mkust = kus.patchTemplates("ferretdb", ["ferretdb-sts.yaml"], data)    
    mspec = kus.kustom_list("ferretdb", mkust, templates=[], data=data)

    if owner:
        kopf.append_owner_reference(mspec['items'], owner)
    else:
        cfg.put("state.ferretdb.spec", mspec)
    
    res = kube.apply(mspec)

    # dynamically detect mongodb pod and wait for readiness
    if res:
        util.wait_for_pod_ready("{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb')].metadata.name}")
        update_system_cm_for_mdb(data)
        logging.info("*** created ferretdb")
        
    return res

def get_ferret_pod_name():
    return util.get_pod_name("{.items[?(@.metadata.labels.app == 'nuvolaris-mongodb')].metadata.name}")    

def update_system_cm_for_mdb(data):
    logging.info("*** annotating configuration for ferretdb nuvolaris user")
    try:        
        mdb_service = util.get_service("{.items[?(@.metadata.name == 'nuvolaris-mongodb-svc')]}")
        if(mdb_service):
            mdb_pod_name = get_ferret_pod_name()        
            mdb_service_name = mdb_service['metadata']['name']            
            mdb_ns = mdb_service['metadata']['namespace']

            data = util.get_postgres_config_data()

            username = urllib.parse.quote(data['postgres_nuvolaris_user'])
            password = urllib.parse.quote(data['postgres_nuvolaris_password'])
            auth = f"{username}:{password}"
            
            mdb_url = f"mongodb://{auth}@{mdb_pod_name}.{mdb_service_name}.{mdb_ns}.svc.cluster.local:27017/nuvolaris?connectTimeoutMS=60000&authMechanism=PLAIN"
            openwhisk.annotate(f"mongodb_url={mdb_url}")
            logging.info("*** saved annotation for mongodb nuvolaris user")            
    except Exception as e:
        logging.error(f"failed to build mongodb_url for nuvolaris database: {e}")  

def delete_by_owner():
    spec = kus.build("ferretdb")
    res = kube.delete(spec)
    logging.info(f"delete ferretdb: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.ferretdb.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete ferretdb: {res}")
    
    return res

def delete(owner=None):
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()

def patch(status, action, owner=None):
    """
    Called the the operator patcher to create/delete ferredb
    """
    try:
        logging.info(f"*** handling request to {action} ferretdb")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['ferretdb']='on'
        else:
            msg = delete(owner)
            status['whisk_create']['ferretdb']='off'

        logging.info(msg)        
        logging.info(f"*** handled request to {action} ferretdb") 
    except Exception as e:
        logging.error('*** failed to update ferretdb: %s' % e)
        status['whisk_create']['ferretdb']='error'             

def _add_mdb_user_metadata(user_metadata, data):
    """
    adds an entry for the mongodb connectivity, i.e
    something like "mongodb://{namespace}:{auth}@nuvolaris-mongodb-0.nuvolaris-mongodb-svc.nuvolaris.svc.cluster.local:27017/{database}?connectTimeoutMS=60000"}
    """ 

    try:
        mdb_service = util.get_service("{.items[?(@.metadata.name == 'nuvolaris-mongodb-svc')]}")

        if(mdb_service):
            mdb_service_name = mdb_service['metadata']['name']            
            mdb_ns = mdb_service['metadata']['namespace']
            mdb_pod_name = get_ferret_pod_name()

            username = urllib.parse.quote(data["username"])
            password = urllib.parse.quote(data["password"])
            auth = f"{username}:{password}"            
            database = data["database"]

            mdb_url = f"mongodb://{auth}@{mdb_pod_name}.{mdb_service_name}.{mdb_ns}.svc.cluster.local:27017/{database}?connectTimeoutMS=60000&authMechanism=PLAIN"
            user_metadata.add_metadata("MONGODB_URL",mdb_url)
        return None
    except Exception as e:
        logging.error(f"failed to build mongodb_url for {ucfg.get('mongodb.database')}: {e}")
        return None

def create_db_user(ucfg: UserConfig, user_metadata: UserMetadata):
    database = ucfg.get('mongodb.database')
    subject = ucfg.get('namespace')
    namespace = ucfg.get('namespace')
    logging.info(f"authorizing new ferretdb database {database}")

    try:
        data = util.get_postgres_config_data()
        data["database"]=f"{database}_ferretdb"
        data["username"]=f"{subject}_ferretdb"
        data["password"]=ucfg.get('mongodb.password')
        data["mode"]="create"
        
        path_to_pgpass = postgres.render_postgres_script(f"{namespace}_ferretdb","pgpass_tpl.properties",data)
        path_to_mdb_script = postgres.render_postgres_script(f"{namespace}_ferretdb","postgres_manage_user_tpl.sql",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.app == 'nuvolaris-postgres')].metadata.name}")      

        if(pod_name):
            res = postgres.exec_psql_command(pod_name,path_to_mdb_script,path_to_pgpass)

            if(res):
                _add_mdb_user_metadata(user_metadata, data)
            return res

        return None
    except Exception as e:
        logging.error(f"failed to add Mongodb database {database}: {e}")
        return None

def delete_db_user(namespace, database):
    logging.info(f"removing ferretdb database {database}")

    try:
        data = util.get_postgres_config_data()        
        data["database"]=f"{database}_ferretdb"
        data["username"]=f"{namespace}_ferretdb"
        data["mode"]="delete"

        path_to_pgpass = postgres.render_postgres_script(f"{namespace}_ferretdb","pgpass_tpl.properties",data)
        path_to_mdb_script = postgres.render_postgres_script(f"{namespace}_ferretdb","postgres_manage_user_tpl.sql",data)
        pod_name = util.get_pod_name("{.items[?(@.metadata.labels.app == 'nuvolaris-postgres')].metadata.name}")

        if(pod_name):
            res = postgres.exec_psql_command(pod_name,path_to_mdb_script,path_to_pgpass)
            return res 

        return None
    except Exception as e:
        logging.error(f"failed to remove Ferretdb database {namespace} authorization id and key: {e}")
        return None        