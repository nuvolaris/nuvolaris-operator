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
import kopf, logging, time, os
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.util as util
import nuvolaris.minio_util as mutil
import nuvolaris.openwhisk as openwhisk
import nuvolaris.apihost_util as apihost_util
import nuvolaris.endpoint as endpoint

from nuvolaris.user_config import UserConfig
from nuvolaris.user_metadata import UserMetadata
from nuvolaris.minio_util import MinioClient
from nuvolaris.ingress_data import IngressData
from nuvolaris.route_data import RouteData

def _add_miniouser_metadata(ucfg: UserConfig, user_metadata:UserMetadata):
    """
    adds entries for minio connectivity MINIO_ENDPOINT, MINIO_PORT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
    this is becasue MINIO
    """ 

    try:
        minio_service =  util.get_service("{.items[?(@.spec.selector.app == 'minio')]}")
        if(minio_service):
            minio_host = f"{minio_service['metadata']['name']}.{minio_service['metadata']['namespace']}.svc.cluster.local"
            access_key = ucfg.get('namespace')
            secret_key = ucfg.get("object-storage.password")
            user_metadata.add_metadata("MINIO_HOST",minio_host)
            user_metadata.add_metadata("MINIO_ACCESS_KEY",access_key)
            user_metadata.add_metadata("MINIO_SECRET_KEY",secret_key)

            ports = list(minio_service['spec']['ports'])
            for port in ports:
                if(port['name']=='minio-api'):
                    user_metadata.add_metadata("MINIO_PORT",port['port'])
        return None
    except Exception as e:
        logging.error(f"failed to build redis_url for {ucfg.get('namespace')}: {e}")
        return None 
    
def find_content_path(filename):
    absolute_path = os.path.dirname(__file__)
    relative_path = "../deploy/content"
    return os.path.join(absolute_path, relative_path, filename)

def create(owner=None):
    logging.info(f"*** configuring minio standalone")

    data = util.get_minio_config_data()

    tplp = ["00-minio-pvc.yaml","01-minio-dep.yaml","02-minio-svc.yaml"]

    if(data['affinity'] or data['tolerations']):
       tplp.append("affinity-tolerance-sts-core-attach.yaml")    

    kust = kus.patchTemplates("minio", tplp, data)
    spec = kus.kustom_list("minio", kust, templates=[], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.minio.spec", spec)

    res = kube.apply(spec)

    # dynamically detect minio pod and wait for readiness
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.app == 'minio')].metadata.name}")
    create_nuv_storage(data)
    create_api_uploader_endpoint(owner)
    logging.info("*** configured minio standalone")
    return res

def _annotate_nuv_metadata(data):
    """
    annotate nuvolaris configmap with entries for minio connectivity MINIO_ENDPOINT, MINIO_PORT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
    this is becasue MINIO
    """ 
    try:
        minio_service =  util.get_service("{.items[?(@.spec.selector.app == 'minio')]}")
        if(minio_service):
            minio_host = f"{minio_service['metadata']['name']}.{minio_service['metadata']['namespace']}.svc.cluster.local"
            access_key = data["minio_nuv_user"]
            secret_key = data["minio_nuv_password"]
            openwhisk.annotate(f"minio_host={minio_host}")
            openwhisk.annotate(f"minio_access_key={access_key}")
            openwhisk.annotate(f"minio_secret_key={secret_key}")

            ports = list(minio_service['spec']['ports'])
            for port in ports:
                if(port['name']=='minio-api'):
                    openwhisk.annotate(f"minio_port={port['port']}")                    
        return None
    except Exception as e:
        logging.error(f"failed to build minio_host for nuvolaris: {e}")
        return None      

def create_nuv_storage(data):
    """
    Creates nuvolaris MINIO custom resources
    """
    logging.info(f"*** configuring MINIO storage for nuvolaris")
    # introduce a 10 seconds delay to be sure that MINIO server is up and running completely as pod readines not to be enough
    time.sleep(10)
    minioClient = mutil.MinioClient()
    res = minioClient.add_user(data["minio_nuv_user"], data["minio_nuv_password"])
    
    if(res):
        _annotate_nuv_metadata(data)
        bucket_policy_names = []

        logging.info(f"*** adding nuvolaris MINIO data bucket")
        res = minioClient.make_bucket("nuvolaris-data")                
        bucket_policy_names.append("nuvolaris-data/*")

        if(res):
            openwhisk.annotate(f"minio_bucket_data=nuvolaris-data")

        logging.info(f"*** adding nuvolaris MINIO static public bucket")
        res = minioClient.make_public_bucket("nuvolaris-web")             
        bucket_policy_names.append("nuvolaris-web/*")

        if(res):
            openwhisk.annotate(f"minio_bucket_static=nuvolaris-web")
            content_path = find_content_path("index.html")

            if(content_path):
                logging.info(f"uploading example content to nuvolaris-web from {content_path}")
                res = minioClient.upload_folder_content(content_path,"nuvolaris-web")
            else:
                logging.warn("could not find example static content to upload")

        if(len(bucket_policy_names)>0):
            logging.info(f"granting rw access to created policies under username {data['minio_nuv_user']}")
            minioClient.assign_rw_bucket_policy_to_user(data["minio_nuv_user"],bucket_policy_names)

        logging.info(f"*** configured MINIO storage for nuvolaris")

def assign_bucket_quota(bucket_name, quota, minioClient:MinioClient):
    if not quota.lower() in ['auto'] and quota.isnumeric():
        logging.info(f"*** setting quota on bucket {bucket_name} with hardlimit to {quota}m")
        res = minioClient.assign_quota_to_bucket(bucket_name,quota)

        if res:
            logging.info(f"*** quota on bucket {bucket_name} set successfully")
    else:
        logging.warn(f"*** skipping quota set on bucket {bucket_name}. Requested quota values is {quota}")


def create_ow_storage(state, ucfg: UserConfig, user_metadata: UserMetadata, owner=None):
    minioClient = mutil.MinioClient()    
    namespace = ucfg.get("namespace")
    secretkey = ucfg.get("object-storage.password")

    logging.info(f"*** configuring storage for namespace {namespace}")

    res = minioClient.add_user(namespace, secretkey)
    state['storage_user']=res

    if(res):
        _add_miniouser_metadata(ucfg, user_metadata)

    bucket_policy_names = []

    if(ucfg.get('object-storage.data.enabled')):
        bucket_name = ucfg.get('object-storage.data.bucket')
        logging.info(f"*** adding private bucket {bucket_name} for {namespace}")
        res = minioClient.make_bucket(bucket_name)               
        bucket_policy_names.append(f"{bucket_name}/*")
        state['storage_data']=res

        if(res):
            user_metadata.add_metadata("MINIO_DATA_BUCKET",bucket_name)

            if ucfg.exists('object-storage.quota'):
                assign_bucket_quota(bucket_name,ucfg.get('object-storage.quota'), minioClient)
    
    if(ucfg.get('object-storage.route.enabled')):
        bucket_name = ucfg.get("object-storage.route.bucket")
        logging.info(f"*** adding public bucket {bucket_name} for {namespace}")
        res = minioClient.make_public_bucket(bucket_name)   
        bucket_policy_names.append(f"{bucket_name}/*")

        if(res):
            user_metadata.add_metadata("MINIO_STATIC_BUCKET",bucket_name)
            
            if ucfg.exists('object-storage.quota'):
                assign_bucket_quota(bucket_name,ucfg.get('object-storage.quota'), minioClient)

        content_path = find_content_path("index.html")

        if(content_path):
            logging.info(f"uploading example content to {bucket_name} from {content_path}")
            res = minioClient.upload_folder_content(content_path,bucket_name)
        else:
            logging.warn("could not find example static content to upload")

        state['storage_route']=res

    if(len(bucket_policy_names)>0):
        logging.info(f"granting rw access to created policies under namespace {namespace}")
        minioClient.assign_rw_bucket_policy_to_user(namespace,bucket_policy_names)        

    return state

def delete_ow_storage(ucfg):
    minioClient = mutil.MinioClient()
    namespace = ucfg.get("namespace")

    if(ucfg.get('object-storage.data.enabled')):
        bucket_name = ucfg.get('object-storage.data.bucket')
        logging.info(f"*** removing private bucket {bucket_name} for {namespace}")
        res = minioClient.force_bucket_remove(bucket_name)

    if(ucfg.get('object-storage.route.enabled')):
        bucket_name = ucfg.get("object-storage.route.bucket")
        logging.info(f"*** removing public bucket {bucket_name} for {namespace}")
        res = minioClient.force_bucket_remove(bucket_name)

    return minioClient.delete_user(namespace)

def delete_by_owner():
    spec = kus.build("minio")
    res = kube.delete(spec)
    logging.info(f"delete minio: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.minio.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete minio: {res}")
    return res

def delete(owner=None):
    delete_api_uploader_endpoint(owner)

    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()

def patch(status, action, owner=None):
    """
    Called by the operator patcher to create/delete minio component
    """
    try:
        logging.info(f"*** handling request to {action} minio")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['minio']='on'
        else:
            msg = delete(owner)
            status['whisk_update']['minio']='off'

        logging.info(msg)        
        logging.info(f"*** hanlded request to {action} minio") 
    except Exception as e:
        logging.error('*** failed to update minio: %s' % e)
        if  action == 'create':
            status['whisk_create']['minio']='error'
        else:            
            status['whisk_update']['minio']='error'

def create_api_uploader_endpoint(owner=None):
    """
    exposes MINIO api in the uploader-api ingress/route
    """
    runtime = cfg.get('nuvolaris.kube')
    apihost = apihost_util.get_apihost(runtime)

    if runtime == 'openshift':           
        return deploy_minio_api_route(apihost, "nuvolaris")
    else:
        return deploy_minio_api_ingress(apihost, "nuvolaris")

def deploy_minio_api_route(apihost,namespace):
    upload = RouteData(apihost)
    upload.with_route_name(endpoint.api_route_name(namespace,"upload"))
    upload.with_service_name("minio")
    upload.with_service_kind("Service")
    upload.with_service_port("9000")
    upload.with_context_path("/api/upload")
    upload.with_rewrite_target("/")

    logging.info(f"*** configuring route for upload")
    path_to_template_yaml = upload.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)        
    return res 

def deploy_minio_api_ingress(apihost, namespace):
    upload = IngressData(apihost)
    upload.with_ingress_name(endpoint.api_ingress_name(namespace,"upload"))
    upload.with_secret_name(endpoint.api_secret_name(namespace))
    upload.with_context_path("/api/upload")
    upload.with_context_regexp("(/|$)(.*)")
    upload.with_rewrite_target("/$2")    
    upload.with_service_name("minio")
    upload.with_service_port("9000")
    upload.with_middleware_ingress_name(endpoint.api_middleware_ingress_name(namespace,"upload"))

    if upload.requires_traefik_middleware():
        logging.info("*** configuring traefik middleware for upload ingress")
        path_to_template_yaml = upload.render_traefik_middleware_template(namespace)
        res = kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)

    logging.info(f"*** configuring static ingress for upload")
    path_to_template_yaml = upload.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)

    return res

def delete_api_uploader_endpoint(owner=None):
    """
    undeploys ingresses for minio apihost
    """    
    logging.info(f"*** removing ingresses for minio upload")
    namespace = "nuvolaris"
    runtime = cfg.get('nuvolaris.kube')
    ingress_class = util.get_ingress_class(runtime)
    
    try:
        res = ""
        if(runtime=='openshift'):
            res = kube.kubectl("delete", "route",endpoint.api_route_name(namespace,"upload"))
            return res

        if(ingress_class == 'traefik'):            
            res = kube.kubectl("delete", "middleware.traefik.containo.us",endpoint.api_middleware_ingress_name(namespace,"upload"))         

        res += kube.kubectl("delete", "ingress",endpoint.api_ingress_name(namespace,"upload"))
        return res
    except Exception as e:
        logging.warn(e)       
        return False                            

