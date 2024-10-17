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
import nuvolaris.apihost_util as apihost_util
import nuvolaris.endpoint as endpoint
import nuvolaris.openwhisk as openwhisk

from nuvolaris.ingress_data import IngressData
from nuvolaris.route_data import RouteData

def deploy_minio_route(apihost,namespace,type,service_name,port,context_path):
    """
    Deploys a generic MINIO route ingress
    param: apihost
    param: namespace
    param: type (s3, console)
    param: service_name (normally it is minio)
    param: port (9000 or 9090)
    paramL context_path (/)
    """
    route = RouteData(apihost)
    route.with_route_name(endpoint.api_route_name(namespace,type))
    route.with_service_name(service_name)
    route.with_service_kind("Service")
    route.with_service_port(port)
    route.with_context_path(context_path)

    logging.info(f"*** configuring minio route for service {service_name}:{port}")
    path_to_template_yaml = route.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)        
    return res

def deploy_minio_ingress(apihost, namespace, type, service_name,port,context_path):
    """
    Deploys a generic MINIO nginx/traefik ingress
    param: apihost
    param: namespace
    param: type (s3, console)
    param: service_name (normally it is minio)
    param: port (9000 or 9090)
    paramL context_path (/)
    """
    ingress = IngressData(apihost)
    ingress.with_ingress_name(endpoint.api_ingress_name(namespace, type))
    ingress.with_secret_name(endpoint.ingress_secret_name(namespace, type))
    ingress.with_context_path(context_path)  
    ingress.with_service_name(service_name)
    ingress.with_service_port(port)

    if ingress.requires_traefik_middleware():
        logging.info(f"*** configuring traefik middleware for {type} ingress")
        path_to_template_yaml = ingress.render_traefik_middleware_template(namespace)
        res = kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)

    logging.info(f"*** configuring static ingress for {type}")
    path_to_template_yaml = ingress.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)

    return res 

def deploy_minio_upload_route(apihost,namespace, type):
    upload = RouteData(apihost)
    upload.with_route_name(endpoint.api_route_name(namespace,type))
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

def deploy_minio_upload_ingress(apihost, namespace, type):
    upload = IngressData(apihost)
    upload.with_ingress_name(endpoint.api_ingress_name(namespace,type))
    upload.with_secret_name(endpoint.api_secret_name(namespace))
    upload.with_context_path("/api/upload")
    upload.with_context_regexp("(/|$)(.*)")
    upload.with_rewrite_target("/$2")    
    upload.with_service_name("minio")
    upload.with_service_port("9000")
    upload.with_middleware_ingress_name(endpoint.api_middleware_ingress_name(namespace,type))

    if upload.requires_traefik_middleware():
        logging.info(f"*** configuring traefik middleware for {type} ingress")
        path_to_template_yaml = upload.render_traefik_middleware_template(namespace)
        res = kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)

    logging.info(f"*** configuring static ingress for {type} ingress")
    path_to_template_yaml = upload.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)

    return res

def create_api_uploader_endpoint(runtime, apihost, owner=None):
    """
    exposes MINIO api in the uploader-api ingress/route
    """
    if runtime == 'openshift':           
        return deploy_minio_upload_route(apihost,"nuvolaris","minio-upload")
    else:
        return deploy_minio_upload_ingress(apihost,"nuvolaris","minio-upload")
    

def create_s3_ingress_endpoint(data, runtime, apihost, owner=None):
    """
    exposes MINIO S3 api ingress ingress/route
    """
    if runtime == 'openshift':
        return deploy_minio_route(apihost,"nuvolaris","minio-s3","minio","9000","/")
    else:
        return deploy_minio_ingress(apihost,"nuvolaris","minio-s3","minio","9000","/")

def create_console_ingress_endpoint(data, runtime, apihost, owner=None):
    """
    exposes MINIO api ingress ingress/route
    """

    if runtime == 'openshift':           
        return deploy_minio_route(apihost,"nuvolaris","minio-console","minio","9090","/")
    else:
        return deploy_minio_ingress(apihost,"nuvolaris","minio-console","minio","9090","/")
    
def get_minio_ingress_hostname(runtime, apihost_url, prefix, hostname_from_config):
    """
    Determine the minio ingress hostname. In auto mode the prefix is appended
    to the configured apihost,, otherwise the one from configuration is used.
    """
    if hostname_from_config in ["auto"]:
        return apihost_util.append_prefix_to_url(apihost_url, prefix)

    return apihost_util.get_ingress_url(runtime, hostname_from_config)

    
def create_minio_ingresses(data, owner=None):
    """
    Creates all the MINIO related ingresses according to provide configuration
    """
    runtime = cfg.get('nuvolaris.kube')
    apihost_url = apihost_util.get_apihost(runtime)
    res = create_api_uploader_endpoint(runtime, apihost_url, owner)

    if data['minio_s3_ingress_enabled']:
        s3_hostname_url = get_minio_ingress_hostname(runtime, apihost_url,"s3",data['minio_s3_ingress_hostname'])
        res += create_s3_ingress_endpoint(data, runtime, s3_hostname_url, owner)

        if res:
            openwhisk.annotate(f"s3_api_url={s3_hostname_url}")
    
    if data['minio_console_ingress_enabled']:
        minio_hostname_url = get_minio_ingress_hostname(runtime, apihost_url,"minio",data['minio_console_ingress_hostname'])
        res += create_console_ingress_endpoint(data, runtime, minio_hostname_url, owner)

        if res:
            openwhisk.annotate(f"s3_console_url={minio_hostname_url}")
            
    # force he s3 API to be localhost:9000 on Kind based deployment.
    if runtime in ["kind"]:
        openwhisk.annotate(f"s3_api_url=http://localhost:9000")     

    return res


def delete_minio_ingress(runtime, namespace, ingress_class, type, owner=None):
    """
    undeploys ingresses for minio apihost
    """    
    logging.info(f"*** removing ingresses for minio upload")
    
    try:
        res = ""
        if(runtime=='openshift'):
            res = kube.kubectl("delete", "route",endpoint.api_route_name(namespace,type))
            return res

        res += kube.kubectl("delete", "ingress",endpoint.api_ingress_name(namespace,type))    

        if(ingress_class == 'traefik'):            
            res = kube.kubectl("delete", "middleware.traefik.containo.us",endpoint.api_middleware_ingress_name(namespace,type))         

        return res
    except Exception as e:
        logging.warn(e)       
        return None    

def delete_minio_ingresses(data, owner=None):
    namespace = "nuvolaris"
    runtime = cfg.get('nuvolaris.kube')
    ingress_class = util.get_ingress_class(runtime)

    res = delete_minio_ingress(runtime, namespace, ingress_class, "minio-upload", owner)

    if data['minio_s3_ingress_enabled']:
        res += delete_minio_ingress(runtime, namespace, ingress_class, "minio-s3", owner)
    
    if data['minio_console_ingress_enabled']:
        res += delete_minio_ingress(runtime, namespace, ingress_class, "minio-console", owner)

    return res