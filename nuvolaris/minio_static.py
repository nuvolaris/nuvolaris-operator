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

def create(owner=None):
    logging.info(f"*** configuring nuvolaris nginx static provider")

    data = {
        "minio_host": cfg.get('minio.host') or "minio",
        "minio_post": cfg.get('minio.port') or "9000",
    }
    
    kust = kus.patchTemplates("nginx-static", ["nginx-static-cm.yaml","nginx-static-sts.yaml"], data)    
    spec = kus.kustom_list("nginx-static", kust, templates=[], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.ngix-static.spec", spec)

    res = kube.apply(spec)

    # dynamically detect nginx pod and wait for readiness
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.app == 'nuvolaris-static')].metadata.name}")

    logging.info("*** configured nuvolaris nginx static provider")
    return res

def static_ingress_name(namespace):
    return f"{namespace}-static-ingress"

def static_route_name(namespace):
    return f"{namespace}-static-route"    

def static_secret_name(namespace):
    return f"{namespace}-static-secret"

def static_middleware_ingress_name(namespace):
    return f"{namespace}-static-ingress-add-prefix"    

def render_static_template(namespace,template,data):
    """
    uses the given template policy to render a final ingress template.
    """  
    out = f"/tmp/__{namespace}_{template}"
    file = ntp.spool_template(template, out, data)
    return os.path.abspath(file)

def render_traefik_middleware_template(namespace,template,data):
    """
    uses the given template policy to render a final ingress template.
    """  
    out = f"/tmp/__{namespace}_{template}"
    file = ntp.spool_template(template, out, data)
    return os.path.abspath(file)

def prepare_static_ingress_data(ucfg, hostname):
    namespace = ucfg.get("namespace")
    runtime = cfg.get('nuvolaris.kube')    
    bucket = ucfg.get('object-storage.route.bucket')
    tls = cfg.get('components.tls') and not runtime=='kind'
    ingress_class = cfg.detect_ingress_class()
    context_path = tls and "/" or f"/{bucket}"
    apply_traefik_prefix_middleware = ingress_class == 'traefik'
    apply_nginx_rewrite_rule = not apply_traefik_prefix_middleware

    data = {
        "namespace":namespace,
        "ingress_name": static_ingress_name(namespace),
        "middleware_ingress_name":static_middleware_ingress_name(namespace),
        "secret_name": static_secret_name(namespace),
        "ingress_class": ingress_class,
        "tls": tls,
        "hostname": hostname,        
        "rewrite_target":f"/{bucket}",
        "service_name": "nuvolaris-static-svc",
        "service_port": 80,
        "context_path":context_path,
        "apply_traefik_prefix_middleware": apply_traefik_prefix_middleware,
        "apply_nginx_rewrite_rule": apply_nginx_rewrite_rule,
        "is_static_ingress":True
    }

    return data

def prepare_static_osh_data(ucfg, hostname):
    namespace = ucfg.get("namespace")
    runtime = cfg.get('nuvolaris.kube')
    bucket = ucfg.get('object-storage.route.bucket')    
    tls = cfg.get('components.tls') and not runtime=='kind'
    context_path = tls and "/" or f"/{bucket}"

    data = {
        "namespace":namespace,
        "route_name": static_route_name(namespace),        
        "tls": tls,
        "hostname": hostname,        
        "rewrite_target":f"/{bucket}",
        "service_name": "nuvolaris-static-svc",
        "service_port": 80,
        "service_kind": "Service",
        "context_path":context_path,
        "is_static_ingress":True,
        "apply_route_rewrite_rule":True
    }

    return data

def create_static_ingress(namespace,data):
    if(data['apply_traefik_prefix_middleware']):
        logging.info(f"*** configuring traefik middleware {data['middleware_ingress_name']}")
        path_to_template_yaml = render_traefik_middleware_template(namespace,"traefik-prefix-middleware-tpl.yaml",data)
        res = kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)

    logging.info(f"*** configuring static ingress endpoint for {namespace}")
    path_to_template_yaml = render_static_template(namespace,"generic-ingress-tpl.yaml",data)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)
    return res 

def create_static_route(namespace,data):
    logging.info(f"*** configuring static ingress route for {namespace}")
    path_to_template_yaml = render_static_template(namespace,"generic-openshift-route-tpl.yaml",data)
    res = kube.kubectl("apply", "-f",path_to_template_yaml)
    os.remove(path_to_template_yaml)
    return res      

                  
def create_ow_static_endpoint(ucfg, user_metadata: UserMetadata, owner=None):
    namespace = ucfg.get("namespace")
    runtime = cfg.get('nuvolaris.kube')
    bucket_name = ucfg.get("object-storage.route.bucket") 
    
    hostname = apihost_util.get_user_static_hostname(runtime, namespace)    
    logging.debug(f"using hostname {hostname} to configure access to user web static space")

    try:     
        user_metadata.add_metadata("STATIC_CONTENT_URL",apihost_util.get_user_static_url(runtime, hostname, bucket_name))
        data = runtime=='openshift' and prepare_static_osh_data(ucfg, hostname) or prepare_static_ingress_data(ucfg, hostname)
        
        if(runtime=='openshift'):
            return create_static_route(namespace, data)
        
        return create_static_ingress(namespace, data)
    except Exception as e:
        logging.warn(e)       
        return False

def delete_ow_static_endpoint(ucfg):
    namespace = ucfg.get("namespace")
    logging.info(f"*** removing static endpoint for {namespace}")
    ingress_class = cfg.detect_ingress_class()
    runtime = cfg.get('nuvolaris.kube')
    
    try:
        if(ingress_class == 'traefik'):            
            middleware_name = static_middleware_ingress_name(namespace)
            kube.kubectl("delete", "middleware.traefik.containo.us",middleware_name)

        if(runtime=='openshift'):
            route_name = static_route_name(namespace)
            return kube.kubectl("delete", "route",route_name)

        ingress_name = static_ingress_name(namespace)
        return kube.kubectl("delete", "ingress",ingress_name)
    except Exception as e:
        logging.warn(e)       
        return False
    
def delete_by_owner():
    spec = kus.build("nginx-static")
    res = kube.delete(spec)
    logging.info(f"delete nuvolaris nginx static provider: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.ngix-static.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete nuvolaris nginx static provider: {res}")
    return res

def delete(owner=None):
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