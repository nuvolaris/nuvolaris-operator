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
import kopf, logging, json, os
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.util as util
import nuvolaris.template as ntp
import nuvolaris.apihost_util as apihost_util

from nuvolaris.user_metadata import UserMetadata
from nuvolaris.ingress_data import IngressData
from nuvolaris.route_data import RouteData

def create(owner=None):
    logging.info(f"*** configuring nuvolaris nginx static provider")
    runtime = cfg.get('nuvolaris.kube')
    data = {
        "name":"nuvolaris-static",
        "container":"nuvolaris-static",
        "size":1,
        "storageClass": cfg.get('nuvolaris.storageclass'),
        "dir":"/var/cache/nginx",
        "minio_host": cfg.get('minio.host') or "minio",
        "minio_port": cfg.get('minio.port') or "9000",
        "applypodsecurity": util.get_enable_pod_security()
    }
    
    tplp = ["nginx-static-cm.yaml","nginx-static-sts.yaml","security-set-attach.yaml","set-attach.yaml"]

    kust = kus.patchTemplates("nginx-static", tplp, data)    
    spec = kus.kustom_list("nginx-static", kust, templates=[], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.nginx-static.spec", spec)

    res = kube.apply(spec)

    # dynamically detect nginx pod and wait for readiness
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.app == 'nuvolaris-static')].metadata.name}")
    create_nuv_static_ingress(runtime, owner)
    logging.info("*** configured nuvolaris nginx static provider")
    return res

def create_nuv_static_ingress(runtime, owner=None):
    apihost_url = apihost_util.get_apihost(runtime)

    if runtime == 'openshift':           
        return deploy_content_route_template("nuvolaris","nuvolaris-web", apihost_url)
    else:
        return deploy_content_ingress_template("nuvolaris","nuvolaris-web",apihost_url)

def static_ingress_name(namespace, default="apihost"):
    return namespace == "nuvolaris" and f"{default}-static-ingress" or f"{namespace}-static-ingress"

def static_route_name(namespace):
    return f"{namespace}-static-route"    

def static_secret_name(namespace):
    return f"{namespace}-crt"

def static_middleware_ingress_name(namespace):
    return f"{namespace}-static-ingress-add-prefix"         

def deploy_content_route_template(namespace, bucket, url):
    logging.info(f"**** configuring static openshift route for url {url}")

    content = RouteData(url)
    content.with_route_name(static_route_name(namespace))
    content.with_needs_rewrite(True)
    content.with_service_name("nuvolaris-static-svc")
    content.with_service_kind("Service")
    content.with_service_port("8080")
    content.with_context_path("/")
    content.with_rewrite_target(f"/{bucket}/")
    
    path_to_template_yaml =  content.render_template(namespace)
    
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)
    return res

def deploy_content_ingress_template(namespace, bucket, url):
    logging.info(f"**** configuring static ingress for url {url}")

    content = IngressData(url)
    content.with_ingress_name(static_ingress_name(namespace))
    content.with_secret_name(static_secret_name(namespace))
    content.with_context_path("/")
    content.with_context_regexp("(.*)")
    content.with_prefix_target(f"/{bucket}")
    content.with_service_name("nuvolaris-static-svc")
    content.with_service_port("8080")
    content.with_middleware_ingress_name(static_middleware_ingress_name(namespace))

    res = ""
    if content.requires_traefik_middleware():
        logging.info("*** configuring traefik middleware")
        path_to_template_yaml = content.render_traefik_middleware_template(namespace)
        res += kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)

    logging.info(f"*** configuring static ingress endpoint for {namespace}")
    path_to_template_yaml = content.render_template(namespace)
    res += kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)
    return res   
                  
def create_ow_static_endpoint(ucfg, user_metadata: UserMetadata, owner=None):
    """
    deploy an ingress to access a generic user web bucket
    """
    runtime = cfg.get('nuvolaris.kube')
    namespace = ucfg.get("namespace")
    apihost = ucfg.get("apihost") or "auto"
    bucket_name = ucfg.get("object-storage.route.bucket")
    
    hostname = apihost_util.get_user_static_hostname(runtime, namespace, apihost)
    logging.debug(f"using hostname {hostname} to configure access to user web static space")

    try:
        apihost_url = apihost_util.get_user_static_url(runtime, hostname)
        user_metadata.add_metadata("STATIC_CONTENT_URL",apihost_url)

        if runtime == 'openshift':
            return deploy_content_route_template(namespace,bucket_name, apihost_url)
        else:
            return deploy_content_ingress_template(namespace,bucket_name, apihost_url)                
    except Exception as e:
        logging.warn(e)       
        return False

def delete_ow_static_endpoint(ucfg):
    """
    undeploy an ingress exposing a generic user web bucket
    """    
    namespace = ucfg.get("namespace")
    runtime = cfg.get('nuvolaris.kube')
    logging.info(f"*** removing static endpoint for {namespace}")
    runtime = cfg.get('nuvolaris.kube')
    ingress_class = util.get_ingress_class(runtime)
    
    try:
        res = ""
        if(runtime=='openshift'):
            route_name = static_route_name(namespace)
            res = kube.kubectl("delete", "route",route_name)
            return res

        if(ingress_class == 'traefik'):            
            middleware_name = static_middleware_ingress_name(namespace)
            res += kube.kubectl("delete", "middleware.traefik.containo.us",middleware_name)            

        ingress_name = static_ingress_name(namespace)
        res += kube.kubectl("delete", "ingress",ingress_name)
        return res
    except Exception as e:
        logging.warn(e)       
        return False
    
def delete_by_owner():
    spec = kus.build("nginx-static")
    res = kube.delete(spec)
    logging.info(f"delete nuvolaris nginx static provider: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.nginx-static.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete nuvolaris nginx static provider: {res}")
    return res

def delete_nuv_ingresses():
    logging.info("*** deleting nuvolaris static ingresses")
    runtime = cfg.get('nuvolaris.kube')
    ingress_class = util.get_ingress_class(runtime)

    try:
        res = ""
        if(runtime=='openshift'):
            route_name = static_route_name("nuvolaris")
            res = kube.kubectl("delete", "route",route_name)
            return res

        if(ingress_class == 'traefik'):            
            middleware_name = static_middleware_ingress_name("nuvolaris")
            res += kube.kubectl("delete", "middleware.traefik.containo.us",middleware_name)            

        ingress_name = static_ingress_name("nuvolaris")
        res += kube.kubectl("delete", "ingress",ingress_name)
        return res
    except Exception as e:
        logging.warn(e)       
        return False
    

def delete(owner=None):
    delete_nuv_ingresses()
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()

def patch(status, action, owner=None):
    """
    Called by the operator patcher to create/delete minio static component
    """
    try:
        logging.info(f"*** handling request to {action} static")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['static']='on'
        else:
            msg = delete(owner)
            status['whisk_create']['static']='off'

        logging.info(msg)        
        logging.info(f"*** hanlded request to {action} static") 
    except Exception as e:
        logging.error('*** failed to update static: %s' % e)
        status['whisk_create']['static']='error'           