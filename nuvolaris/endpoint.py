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
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.openwhisk as openwhisk
import nuvolaris.apihost_util as apihost_util

from nuvolaris.ingress_data import IngressData
from nuvolaris.route_data import RouteData

def create_endpoint_routes(owner, apihost):
    logging.info(f"**** configuring openshift route based endpoint for apihost {apihost}")

    api = RouteData(apihost)
    api.with_route_name("openwhisk-route")
    api.with_needs_rewrite(False)
    api.with_service_name("controller-ip")
    api.with_service_kind("Service")
    api.with_service_port("8080")
    api.with_context_path("/")

    api_spec = api.build_route_spec("openwhisk-endpoint","_nuv_route_template.yaml")

    if owner:
        kopf.append_owner_reference(api_spec['items'], owner)
    else:
        cfg.put("state.endpoint.api.spec", api_spec)

    return kube.apply(api_spec)


def create_endpoint_ingresses(owner, apihost):
    logging.info(f"**** configuring ingresses based endpoint for apihost {apihost}")

    api = IngressData(apihost)
    api.with_ingress_name("apihost")
    api.with_secret_name("nuvolaris-letsencrypt-secret")
    api.with_path_type("ImplementationSpecific")
    api.with_context_path("/api/v1(/|$)(.*)")
    api.with_rewrite_target("/api/v1/$2")
    api.with_service_name("controller")
    api.with_service_port("3233")
    api.with_needs_rewrite(True)

    my = IngressData(apihost)
    my.with_ingress_name("apihost-my")
    my.with_secret_name("nuvolaris-letsencrypt-secret")
    my.with_path_type("ImplementationSpecific")
    my.with_context_path("/api/my(/|$)(.*)")
    my.with_rewrite_target("/api/v1/web/namespace/nuvolaris/$2")
    my.with_service_name("controller")
    my.with_service_port("3233")
    my.with_needs_rewrite(True)

    api_spec = api.build_ingress_spec("openwhisk-endpoint","_nuv_api_ingress.yaml")
    my_spec = my.build_ingress_spec("openwhisk-endpoint","_nuv_my_ingress.yaml")

    if owner:
        kopf.append_owner_reference(api_spec['items'], owner)
        kopf.append_owner_reference(my_spec['items'], owner)
    else:
        cfg.put("state.endpoint.api.spec", api_spec)
        cfg.put("state.endpoint.my.spec", my_spec)

    res = kube.apply(api_spec)
    res += kube.apply(my_spec)    

    return res


def create(owner=None):
    runtime = cfg.get('nuvolaris.kube')
    apihost = apihost_util.get_apihost(runtime)

    logging.info(f"*** Saving configuration for OpenWishk apihost={apihost}")
    openwhisk.annotate(f"apihost={apihost}")
    cfg.put("config.apihost", apihost)

    if runtime == 'openshift':
        return create_endpoint_routes(owner, apihost)
    else:
        return create_endpoint_ingresses(owner, apihost)
    
def delete_by_owner():
    runtime = cfg.get('nuvolaris.kube')
    tpls = runtime=='openshift' and["_nuv_route_template.yaml"] or ["_nuv_api_ingress.yaml","_nuv_my_ingress.yaml"]

    res = False

    for tpl in tpls:
        res = kube.kubectl("delete", "-f", f"deploy/openwhisk-endpoint/{tpl}")
        logging.info(f"delete template {tpl}: {res}")

    return res

def delete_by_spec():
    api_spec = cfg.get("state.endpoint.api.spec")
    my_spec = cfg.get("state.endpoint.my.spec")
    res = False
    if api_spec:
        res = kube.delete(api_spec)
    
    if my_spec:
        res = kube.delete(my_spec)

    return res

def delete(owner=None):
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()

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
