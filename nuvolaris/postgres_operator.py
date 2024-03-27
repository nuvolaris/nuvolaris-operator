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

import kopf, json, time, logging, os
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.util as util
import nuvolaris.openwhisk as openwhisk
import nuvolaris.template as ntp
import urllib.parse

from nuvolaris.user_config import UserConfig
from nuvolaris.user_metadata import UserMetadata

def create(owner=None):
    """
    Deploys the postgres using kubegres operator and wait for the operator to be ready.
    """
    logging.info("*** creating kubegres-operator")        
    pg_cm_data = util.postgres_manager_affinity_tolerations_data()
    pg_op_kust = kus.patchTemplates("postgres-operator",templates=["affinity-tolerance-dep-core-attach.yaml"], data=pg_cm_data)
    spec = kus.kustom_list("postgres-operator",pg_op_kust, templates=[], data={})

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.postgres-operator.spec", spec)

    res = kube.apply(spec)
    logging.info("*** created postgres operator")
    
    #wait for postgres_operator to be ready
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.control-plane == 'controller-manager')].metadata.name}")
    
    logging.info("*** creating a postgres instance")
    data = util.get_postgres_config_data()    
    mkust = kus.patchTemplates("postgres-operator-deploy",templates=["postgres.yaml"], data=data)
    mkust += kus.patchGenericEntry("Secret","postgres-nuvolaris-secret","/stringData/superUserPassword",data['postgres_root_password'])
    mkust += kus.patchGenericEntry("Secret","postgres-nuvolaris-secret","/stringData/replicationUserPassword",data['postgres_root_replica_password'])        
    mkust += kus.patchGenericEntry("Secret","postgres-nuvolaris-secret","/stringData/nuvolarisUserPassword",data['postgres_nuvolaris_password'])     
    mspec = kus.kustom_list("postgres-operator-deploy", mkust, templates=[],data={})

    if owner:
        kopf.append_owner_reference(mspec['items'], owner)
    else:
        cfg.put("state.postgres.spec", mspec)
    
    res += kube.apply(mspec)
    # dynamically detect postgres pod and wait for readiness
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.app == 'nuvolaris-postgres')].metadata.name}")

    if(res):
        util.wait_for_service("{.items[?(@.metadata.labels.replicationRole == 'primary')]}")        

    if data['backup']:
        logging.info("*** activating nuvolaris-postgres backup")
        backup_data = util.get_postgres_backup_data()
        tplp = ["set-attach.yaml","postgres-backup-sts.yaml"]

        if(backup_data['affinity'] or backup_data['tolerations']):
            tplp.append("affinity-tolerance-sts-core-attach.yaml")

        bkust = kus.patchTemplates("postgres-backup",templates=tplp, data=backup_data)
        bspec = kus.kustom_list("postgres-backup", bkust, templates=[],data={})

        if owner:
            kopf.append_owner_reference(bspec['items'], owner)
        else:
            cfg.put("state.postgres-backup.spec", bspec)

        res += kube.apply(bspec)

    if res:
        update_system_cm_for_pdb(data)        

    return res


def update_system_cm_for_pdb(data):
    logging.info("*** annotating configuration for postgres nuvolaris user")
    try:        
        pdb_service = util.get_service_by_selector("app=nuvolaris-postgres","{.items[?(@.metadata.labels.replicationRole == 'primary')]}")
        
        if(pdb_service):             
            pdb_service_name = pdb_service['metadata']['name']
            pdb_ns = pdb_service['metadata']['namespace']
            pdb_host = f"{pdb_service_name}.{pdb_ns}.svc.cluster.local"            
            pdb_port = pdb_service['spec']['ports'][0]['port']
            username = "nuvolaris"
            database = "nuvolaris"
            password = urllib.parse.quote(data['postgres_nuvolaris_password'])
            auth = f"{username}:{password}"            
            pdb_url = f"postgresql://{auth}@{pdb_service_name}.{pdb_ns}.svc.cluster.local:{pdb_port}/{database}"

            openwhisk.annotate(f"postgres_host={pdb_host}")
            openwhisk.annotate(f"postgres_port={pdb_port}")
            openwhisk.annotate(f"postgres_database={database}")
            openwhisk.annotate(f"postgres_username={username}")
            openwhisk.annotate(f"postgres_password={password}")
            openwhisk.annotate(f"postgres_url={pdb_url}")

            logging.info("*** saved annotation for postgres nuvolaris user")            
    except Exception as e:
        logging.error(f"failed to build postgres data for nuvolaris database: {e}")

def get_base_postgres_url(data):    
    try:        
        pdb_service = util.get_service_by_selector("app=nuvolaris-postgres","{.items[?(@.metadata.labels.replicationRole == 'primary')]}")

        if(pdb_service):             
            pdb_service_name = pdb_service['metadata']['name']
            pdb_ns = pdb_service['metadata']['namespace']
            pdb_host = f"{pdb_service_name}.{pdb_ns}.svc.cluster.local"            
            pdb_port = pdb_service['spec']['ports'][0]['port']
            username = "nuvolaris"
            database = "nuvolaris"
            password = urllib.parse.quote(data['postgres_nuvolaris_password'])
            auth = f"{username}:{password}"            
            return f"postgresql://{auth}@{pdb_service_name}.{pdb_ns}.svc.cluster.local:{pdb_port}"
           
    except Exception as e:
        logging.error(f"failed to build base postgres URL: {e}")        

def _add_pdb_user_metadata(ucfg, user_metadata):
    """
    adds an entry for the postgres connectivity, i.e   
    """ 

    try:
        pdb_service = util.get_service_by_selector("app=nuvolaris-postgres","{.items[?(@.metadata.labels.replicationRole == 'primary')]}")

        if(pdb_service):
            pdb_service_name = pdb_service['metadata']['name']
            pdb_ns = pdb_service['metadata']['namespace']
            pdb_host = f"{pdb_service_name}.{pdb_ns}.svc.cluster.local"            
            pdb_port = pdb_service['spec']['ports'][0]['port']
            username = urllib.parse.quote(ucfg.get('namespace'))
            password = urllib.parse.quote(ucfg.get('postgres.password'))
            auth = f"{username}:{password}"
            pdb_url = f"postgresql://{auth}@{pdb_service_name}.{pdb_ns}.svc.cluster.local:{pdb_port}/{ucfg.get('postgres.database')}"

            user_metadata.add_metadata("POSTGRES_HOST",pdb_host)
            user_metadata.add_metadata("POSTGRES_PORT",pdb_port)
            user_metadata.add_metadata("POSTGRES_DATABASE",ucfg.get('postgres.database')) 
            user_metadata.add_metadata("POSTGRES_USERNAME",ucfg.get('namespace')) 
            user_metadata.add_metadata("POSTGRES_PASSWORD",ucfg.get('postgres.password'))
            user_metadata.add_metadata("POSTGRES_URL",pdb_url)
        return None
    except Exception as e:
        logging.error(f"failed to build postgres_host for {ucfg.get('postgres.database')}: {e}")
        return None 

def render_postgres_script(namespace,template,data):
    """
    uses the given template to render a sh script to execute via psql.
    """  
    out = f"/tmp/__{namespace}_{template}"
    file = ntp.spool_template(template, out, data)
    return os.path.abspath(file)

def exec_psql_command(pod_name,path_to_psql_script,path_to_pgpass):
    logging.info(f"passing script {path_to_psql_script} to pod {pod_name}")
    res = kube.kubectl("cp",path_to_psql_script,f"{pod_name}:{path_to_psql_script}")
    res = kube.kubectl("cp",path_to_pgpass,f"{pod_name}:/tmp/.pgpass")
    res = kube.kubectl("exec","-it",pod_name,"--","/bin/bash","-c",f"chmod 600 /tmp/.pgpass")
    res = kube.kubectl("exec","-it",pod_name,"--","/bin/bash","-c",f"PGPASSFILE='/tmp/.pgpass' psql --username postgres --dbname postgres -f {path_to_psql_script}")
    os.remove(path_to_psql_script)
    os.remove(path_to_pgpass)
    return res

def create_db_user(ucfg: UserConfig, user_metadata: UserMetadata):
    database = ucfg.get('postgres.database')
    logging.info(f"authorizing new postgres database {database}")

    try:
        data = util.get_postgres_config_data()        
        data["database"]=database
        data["username"]=ucfg.get('namespace')
        data["password"]=ucfg.get('postgres.password')
        data["mode"]="create"        

        path_to_pgpass = render_postgres_script(ucfg.get('namespace'),"pgpass_tpl.properties",data)
        path_to_mdb_script = render_postgres_script(ucfg.get('namespace'),"postgres_manage_user_tpl.sql",data)
        pod_name = util.get_pod_name_by_selector("app=nuvolaris-postgres","{.items[?(@.metadata.labels.replicationRole == 'primary')].metadata.name}")

        if(pod_name):
            res = exec_psql_command(pod_name,path_to_mdb_script,path_to_pgpass)

            if res:
                _add_pdb_user_metadata(ucfg, user_metadata)
                return res
            else:
                logging.error(f"failed to add Postgres database {database}") 

        return None
    except Exception as e:
        logging.error(f"failed to add Postgres database {database}: {e}")
        return None

def delete_db_user(namespace, database):
    logging.info(f"removing postgres database {database}")

    try:
        data = util.get_postgres_config_data()
        data["username"]=namespace
        data["database"]=database
        data["mode"]="delete"

        path_to_pgpass = render_postgres_script(namespace,"pgpass_tpl.properties",data)
        path_to_mdb_script = render_postgres_script(namespace,"postgres_manage_user_tpl.sql",data)
        pod_name = util.get_pod_name_by_selector("app=nuvolaris-postgres","{.items[?(@.metadata.labels.replicationRole == 'primary')].metadata.name}")

        if(pod_name):
            res = exec_psql_command(pod_name,path_to_mdb_script,path_to_pgpass)
            return res 

        return None
    except Exception as e:
        logging.error(f"failed to remove Postgres database {namespace} authorization id and key: {e}")
        return None

def delete_by_owner():
    spec = kus.build("postgres-backup")
    res = kube.delete(spec)
    logging.info(f"delete postgres backup: {res}")
    spec = kus.build("postgres-operator-deploy")
    res = kube.delete(spec)
    logging.info(f"delete postgres: {res}")
    spec = kus.build("postgres-operator")
    res = kube.delete(spec)    
    logging.info(f"delete postgres-operator: {res}") 
    return res

def delete_by_spec():
    spec = cfg.get("state.postgres-backup.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete postgres backup: {res}")

    spec = cfg.get("state.postgres.spec")    
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete postgres: {res}")

    spec = cfg.get("state.postgres-operator.spec")
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete postgres-operator: {res}")        
    return res

def delete(owner=None):
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()

def patch(status, action, owner=None):
    """
    Called by the operator patcher to create/delete postgres component
    """
    try:
        logging.info(f"*** handling request to {action} postgres")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['postgres']='on'
        else:
            msg = delete(owner)
            status['whisk_update']['postgres']='off'

        logging.info(msg)        
        logging.info(f"*** handled request to {action} postgres") 
    except Exception as e:
        logging.error('*** failed to update postgres: %s' % e)
        if  action == 'create':
            status['whisk_create']['postgres']='error'
        else:            
            status['whisk_update']['postgres']='error'                    