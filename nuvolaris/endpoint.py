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

def api_route_name(namespace):
    return f"{namespace}-api-route"    

def api_secret_name(namespace):
    return f"{namespace}-crt"

def api_middleware_ingress_name(namespace,ingress):
    return f"{namespace}-{ingress}-api-ingress-add-prefix"

def deploy_endpoint_routes(apihost,namespace):
    logging.info(f"**** configuring openshift route based endpoint for apihost {apihost}")

    api = RouteData(apihost)
    api.with_route_name(api_route_name(namespace))
    api.with_needs_rewrite(False)
    api.with_service_name("controller-ip")
    api.with_service_kind("Service")
    api.with_service_port("8080")
    api.with_context_path("/")

    path_to_template_yaml =  api.render_template("nuvolaris")
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)
    return res
    

def deploy_endpoint_ingresses(apihost, namespace):
    logging.info(f"**** configuring ingresses based endpoint for apihost {apihost}")   
    api = IngressData(apihost)
    api.with_ingress_name(api_ingress_name(namespace,"apihost"))
    api.with_secret_name(api_secret_name(namespace))
    api.with_path_type("ImplementationSpecific")
    api.with_context_path("/api/v1(/|$)(.*)")
    api.with_rewrite_target("/api/v1/$2")
    api.with_service_name("controller")
    api.with_service_port("3233")
    api.with_needs_rewrite(True)
    api.with_middleware_ingress_name(api_middleware_ingress_name(namespace,"apihost"))

    my = IngressData(apihost)
    my.with_ingress_name(api_ingress_name(namespace,"apihost-my"))
    my.with_secret_name(api_secret_name(namespace))
    my.with_path_type("ImplementationSpecific")
    my.with_context_path("/api/my(/|$)(.*)")
    my.with_rewrite_target(f"/api/v1/web/namespace/{namespace}/$2")
    my.with_service_name("controller")
    my.with_service_port("3233")
    my.with_needs_rewrite(True)
    my.with_middleware_ingress_name(api_middleware_ingress_name(namespace,"apihost-my"))

    if api.requires_traefik_middleware():
        logging.info("*** configuring traefik middleware for apihost ingress")
        path_to_template_yaml = api.render_traefik_middleware_template(namespace)
        res = kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)

    if my.requires_traefik_middleware():
        logging.info("*** configuring traefik middleware for apihost-my ingress")
        path_to_template_yaml = my.render_traefik_middleware_template(namespace)
        res = kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)        

    logging.info(f"*** configuring static ingress for apihost")
    path_to_template_yaml = api.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)

    logging.info(f"*** configuring static ingress for apihost-my")
    path_to_template_yaml = my.render_template(namespace)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)    
    return res 


def create(owner=None):
    runtime = cfg.get('nuvolaris.kube')
    apihost = apihost_util.get_apihost(runtime)

    logging.info(f"*** Saving configuration for OpenWishk apihost={apihost}")
    openwhisk.annotate(f"apihost={apihost}")
    cfg.put("config.apihost", apihost)
    
    if runtime == 'openshift':
        return deploy_endpoint_routes(apihost,"nuvolaris")
    else:
        return deploy_endpoint_ingresses(apihost,"nuvolaris")

def delete(owner=None):
    """
    undeploys  ingresses for the nuvolaris apihost
    """    
    logging.info(f"*** removing ingresses for nuvolaris apihost")
    namespace = "nuvolaris"
    runtime = cfg.get('nuvolaris.kube')        
    ingress_class = util.get_ingress_class(runtime)
    
    try:
        res = ""
        if(runtime=='openshift'):
            res = kube.kubectl("delete", "route",api_route_name(namespace))
            return res

        if(ingress_class == 'traefik'):            
            res = kube.kubectl("delete", "middleware.traefik.containo.us",api_middleware_ingress_name(namespace,"apihost"))
            res += kube.kubectl("delete", "middleware.traefik.containo.us",api_middleware_ingress_name(namespace,"apihost-my"))          

        res += kube.kubectl("delete", "ingress",api_ingress_name(namespace,"apihost"))
        res += kube.kubectl("delete", "ingress",api_ingress_name(namespace,"apihost-my"))
        return res
    except Exception as e:
        logging.warn(e)       
        return False

def patch(status, action, owner=None):
    """
    Called the the operator patcher to create/update/delete endpoint for apihost
    """
    try:
        logging.info(f"*** handling request to {action} endpoint")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['endpoint']='on'
        elif action == 'delete':
            msg = delete(owner)
            status['whisk_create']['endpoint']='off'
        else:
            msg = create(owner)
            status['whisk_create']['endpoint']='updated'

        logging.info(msg)        
        logging.info(f"*** handled request to {action} endpoint") 
    except Exception as e:
        logging.error('*** failed to update endpoint: %s' % e)
        status['whisk_create']['endpoint']='error'

def create_ow_api_endpoint(ucfg, user_metadata: UserMetadata, owner=None):
    """
    deploy ingresses to access a generic user api and ow api in a CORS firendly way
    """
    runtime = cfg.get('nuvolaris.kube')
    namespace = ucfg.get("namespace")
    apihost = ucfg.get("apihost") or "auto"
    hostname = apihost_util.get_user_static_hostname(runtime, namespace, apihost)
    logging.debug(f"using hostname {hostname} to configure access to user openwhisk api")

    try:
        apihost_url = apihost_util.get_user_static_url(runtime, hostname)
        
        my_url = apihost_util.get_user_api_url(runtime, hostname,"/api/my")
        api_url = apihost_util.get_user_api_url(runtime, hostname,"/api/v1")
        user_metadata.add_metadata("WEB_API__URL",my_url)
        user_metadata.add_metadata("OW_API_URL",api_url)

        if runtime == 'openshift':
            return deploy_endpoint_routes(apihost_url, namespace)
        else:
            return deploy_endpoint_ingresses(apihost_url, namespace)                
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
            route_name = api_route_name(namespace)
            res = kube.kubectl("delete", "route",route_name)
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
