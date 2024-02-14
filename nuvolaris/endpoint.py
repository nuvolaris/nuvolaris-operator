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
import kopf, logging, json, time
import os
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.openwhisk as openwhisk
import nuvolaris.apihost_util as apihost_util
import nuvolaris.util as util

from nuvolaris.ingress_data import IngressData
from nuvolaris.route_data import RouteData
from nuvolaris.user_metadata import UserMetadata

def api_ingress_name(namespace, ingress="apishost"):
    return namespace == "nuvolaris" and ingress or f"{namespace}-{ingress}-api-ingress"

def api_route_name(namespace,route="apishost"):
    return namespace == "nuvolaris" and route or f"{namespace}-{route}-api-route"

def api_secret_name(namespace):
    return f"{namespace}-crt"

def api_middleware_ingress_name(namespace,ingress):
    return f"{namespace}-{ingress}-api-ingress-add-prefix"

def deploy_info_route(apihost,namespace):
    info = RouteData(apihost)
    info.with_route_name(api_route_name(namespace,"apihost-info"))
    info.with_service_name("controller-ip")
    info.with_service_kind("Service")
    info.with_service_port("8080")
    info.with_context_path("/api/info")
    info.with_rewrite_target("/")

    logging.info(f"*** configuring route for apihost-info")
    path_to_template_yaml =  info.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)        
    return res 

def deploy_api_routes(apihost,namespace,should_create_www=False):
    logging.info(f"**** configuring openshift route based endpoint for apihost {apihost}")

    api = RouteData(apihost)
    api.with_route_name(api_route_name(namespace,"apihost"))
    api.with_service_name("controller-ip")
    api.with_service_kind("Service")
    api.with_service_port("8080")
    api.with_context_path("/api/v1")
    api.with_rewrite_target("/api/v1")

    my = RouteData(apihost)
    my.with_route_name(api_route_name(namespace,"apihost-my"))
    my.with_service_name("controller-ip")
    my.with_service_kind("Service")
    my.with_service_port("8080")
    my.with_context_path("/api/my")
    my.with_rewrite_target(f"/api/v1/web/namespace/{namespace}")  

    logging.info(f"*** configuring route for apihost")
    path_to_template_yaml =  api.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)

    logging.info(f"*** configuring route for apihost-my")
    path_to_template_yaml =  my.render_template(namespace)
    res += kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml) 

    if should_create_www:
            www_my = RouteData(apihost)
            www_my.with_route_name(api_route_name(namespace,"apihost-www-my"))
            www_my.with_service_name("controller-ip")
            www_my.with_service_kind("Service")
            www_my.with_service_port("8080")
            www_my.with_context_path("/api/my")
            www_my.with_rewrite_target(f"/api/v1/web/namespace/{namespace}") 

            logging.info(f"*** configuring route for apihost-www-my")
            path_to_template_yaml =  www_my.render_template(namespace)
            res += kube.kubectl("apply", "-f",path_to_template_yaml)
            os.remove(path_to_template_yaml) 
        
    return res

def deploy_info_ingress(apihost, namespace):
    res = ""
    info = IngressData(apihost)
    info.with_ingress_name(api_ingress_name(namespace,"apihost-info"))
    info.with_secret_name(api_secret_name(namespace))
    info.with_context_path("/api/info")
    info.with_context_regexp("(/|$)(.*)")
    info.with_rewrite_target("/$2")    
    info.with_service_name("controller")
    info.with_service_port("3233")
    info.with_middleware_ingress_name(api_middleware_ingress_name(namespace,"apihost-info"))

    if info.requires_traefik_middleware():
        logging.info("*** configuring traefik middleware for apihost-info ingress")
        path_to_template_yaml = info.render_traefik_middleware_template(namespace)
        res += kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)

    logging.info(f"*** configuring static ingress for apihost-info")
    path_to_template_yaml = info.render_template(namespace)
    res += kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)

    return res     
    

def deploy_api_ingresses(apihost, namespace,should_create_www=False):
    logging.info(f"**** configuring ingresses based endpoint for apihost {apihost}")
    res = ""   
    api = IngressData(apihost)
    api.with_ingress_name(api_ingress_name(namespace,"apihost"))
    api.with_secret_name(api_secret_name(namespace))
    api.with_context_path("/api/v1")
    api.with_context_regexp("(/|$)(.*)")
    api.with_rewrite_target("/api/v1/$2")
    api.with_service_name("controller")
    api.with_service_port("3233")
    api.with_middleware_ingress_name(api_middleware_ingress_name(namespace,"apihost"))

    my = IngressData(apihost)
    my.with_ingress_name(api_ingress_name(namespace,"apihost-my"))
    my.with_secret_name(api_secret_name(namespace))
    my.with_context_path("/api/my")
    my.with_context_regexp("(/|$)(.*)")
    my.with_rewrite_target(f"/api/v1/web/{namespace}/$2")
    my.with_service_name("controller")
    my.with_service_port("3233")
    my.with_middleware_ingress_name(api_middleware_ingress_name(namespace,"apihost-my"))

    if api.requires_traefik_middleware():
        logging.info("*** configuring traefik middleware for apihost ingress")
        path_to_template_yaml = api.render_traefik_middleware_template(namespace)
        res += kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)

    if my.requires_traefik_middleware():
        logging.info("*** configuring traefik middleware for apihost-my ingress")
        path_to_template_yaml = my.render_traefik_middleware_template(namespace)
        res += kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)        

    logging.info(f"*** configuring static ingress for apihost")
    path_to_template_yaml = api.render_template(namespace)
    res += kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)

    logging.info(f"*** configuring static ingress for apihost-my")
    path_to_template_yaml = my.render_template(namespace)
    res += kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)

    if should_create_www:
        www_my = IngressData(apihost)
        www_my.with_ingress_name(api_ingress_name(namespace,"apihost-www-my"))
        www_my.with_secret_name(api_secret_name(namespace)+"-www")
        www_my.with_context_path("/api/my")
        www_my.with_context_regexp("(/|$)(.*)")
        www_my.with_rewrite_target(f"/api/v1/web/{namespace}/$2")
        www_my.with_service_name("controller")
        www_my.with_service_port("3233")
        www_my.with_middleware_ingress_name(api_middleware_ingress_name(namespace,"apihost-www-my"))

        if www_my.requires_traefik_middleware():
            logging.info("*** configuring traefik middleware for apihost-www-my ingress")
            path_to_template_yaml = www_my.render_traefik_middleware_template(namespace)
            res += kube.kubectl("apply", "-f",path_to_template_yaml)
            os.remove(path_to_template_yaml)

        logging.info(f"*** configuring static ingress for apihost-www-my")
        path_to_template_yaml = www_my.render_template(namespace)
        res += kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)                     

    return res 

def create(owner=None):
    runtime = cfg.get('nuvolaris.kube')
    apihost = apihost_util.get_apihost(runtime)
    runtime = cfg.get('nuvolaris.kube')
    hostname = apihost_util.extract_hostname(apihost)
    should_create_www = "www" not in hostname and runtime not in ["kind"]

    logging.info(f"*** Saving configuration for OpenWishk apihost={apihost}")
    openwhisk.annotate(f"apihost={apihost}")
    cfg.put("config.apihost", apihost)
    
    if runtime == 'openshift':
        res = deploy_info_route(apihost,"nuvolaris")
        return deploy_api_routes(apihost,"nuvolaris",should_create_www)
    else:
        res = deploy_info_ingress(apihost,"nuvolaris")
        return deploy_api_ingresses(apihost,"nuvolaris",should_create_www)

def delete(owner=None):
    """
    undeploys ingresses for nuvolaris apihost
    """    
    logging.info(f"*** removing ingresses for nuvolaris apihost")
    namespace = "nuvolaris"
    runtime = cfg.get('nuvolaris.kube')        
    ingress_class = util.get_ingress_class(runtime)
    apihost = apihost_util.get_apihost(runtime)
    hostname = apihost_util.extract_hostname(apihost)
    should_delete_www = "www" not in hostname and runtime not in ["kind"]
    
    try:
        res = ""
        if(runtime=='openshift'):
            res = kube.kubectl("delete", "route",api_route_name(namespace,"apihost"))
            res += kube.kubectl("delete", "route",api_route_name(namespace,"apihost-my"))
            res += kube.kubectl("delete", "route",api_route_name(namespace,"apihost-info"))

            if should_delete_www:
                res += kube.kubectl("delete", "route",api_route_name(namespace,"apihost-www-my"))
            return res

        if(ingress_class == 'traefik'):            
            res = kube.kubectl("delete", "middleware.traefik.containo.us",api_middleware_ingress_name(namespace,"apihost"))
            res += kube.kubectl("delete", "middleware.traefik.containo.us",api_middleware_ingress_name(namespace,"apihost-my"))
            res += kube.kubectl("delete", "middleware.traefik.containo.us",api_middleware_ingress_name(namespace,"apihost-info"))
            if should_delete_www:
                res += kube.kubectl("delete", "middleware.traefik.containo.us",api_middleware_ingress_name(namespace,"apihost-www-my"))          

        res += kube.kubectl("delete", "ingress",api_ingress_name(namespace,"apihost"))
        res += kube.kubectl("delete", "ingress",api_ingress_name(namespace,"apihost-my"))
        res += kube.kubectl("delete", "ingress",api_ingress_name(namespace,"apihost-info"))
        if should_delete_www:
            res += kube.kubectl("delete", "ingress",api_ingress_name(namespace,"apihost-www-my"))
        return res
    except Exception as e:
        logging.warn(e)       
        return False

def patch(status, action, owner=None):
    """
    Called by the operator patcher to create/update/delete endpoint for apihost
    """
    try:
        logging.info(f"*** handling request to {action} endpoint")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['endpoint']='on'
        elif action == 'delete':
            msg = delete(owner)
            status['whisk_update']['endpoint']='off'
        else:
            msg = create(owner)
            status['whisk_update']['endpoint']='updated'

        logging.info(msg)        
        logging.info(f"*** handled request to {action} endpoint") 
    except Exception as e:
        logging.error('*** failed to update endpoint: %s' % e)
        if  action == 'create':
            status['whisk_create']['endpoint']='error'
        else:            
            status['whisk_update']['endpoint']='error'  

def create_ow_api_endpoint(ucfg, user_metadata: UserMetadata, owner=None):
    """
    deploy ingresses to access a generic user api and ow api in a CORS friendly way
    currently this is not supported for openshift
    """
    runtime = cfg.get('nuvolaris.kube')
    namespace = ucfg.get("namespace")
    apihost = ucfg.get("apihost") or "auto"
    hostname = apihost_util.get_user_static_hostname(runtime, namespace, apihost)
    logging.debug(f"using hostname {hostname} to configure access to user openwhisk api")

    try:
        apihost_url = apihost_util.get_user_static_url(runtime, hostname)
        my_url = apihost_util.get_user_api_url(runtime, hostname,"api/my")
        user_metadata.add_metadata("USER_REST_API_URL",my_url)
        user_metadata.add_metadata("USER_V1_API_URL",apihost_url)

        if runtime == 'openshift':
            return deploy_api_routes(apihost_url, namespace)
        else:
            return deploy_api_ingresses(apihost_url, namespace)                
    except Exception as e:
        logging.warn(e)       
        return False

def delete_ow_api_endpoint(ucfg):
    """
    undeploy the ingresses
    """    
    namespace = ucfg.get("namespace")
    runtime = cfg.get('nuvolaris.kube')
    logging.info(f"*** removing api endpoint for {namespace}")
    runtime = cfg.get('nuvolaris.kube')
    ingress_class = util.get_ingress_class(runtime)
    
    try:
        res = ""
        if(runtime=='openshift'):            
            res = kube.kubectl("delete", "route",api_route_name(namespace,"apihost"))
            res += kube.kubectl("delete", "route",api_route_name(namespace,"apihost-my"))
            return res

        if(ingress_class == 'traefik'):                        
            res += kube.kubectl("delete", "middleware.traefik.containo.us",api_middleware_ingress_name(namespace,"apihost"))
            res += kube.kubectl("delete", "middleware.traefik.containo.us",api_middleware_ingress_name(namespace,"apihost-my"))             

        res += kube.kubectl("delete", "ingress",api_ingress_name(namespace,"apihost"))
        res += kube.kubectl("delete", "ingress",api_ingress_name(namespace,"apihost-my"))
        return res
    except Exception as e:
        logging.warn(e)       
        return False                             
