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
import nuvolaris.util as util
import nuvolaris.apihost_util as apihost_util
import urllib.parse

def get_ingress_data(apihost, tls):
    url = urllib.parse.urlparse(apihost)
    hostname = url.hostname    
    ingress_class = cfg.detect_ingress_class()

    data = {
        "hostname":hostname,
        "ingress_class":ingress_class,
        "tls":tls,
        "secret_name":"nuvolaris-letsencrypt-secret",
        "ingress_name":"apihost",
        "service_name":"controller",
        "service_port":"3233",
        "context_path":"/"
    }

    return data

def get_osh_data(apihost, tls):
    url = urllib.parse.urlparse(apihost)
    hostname = url.hostname    
    ingress_class = cfg.detect_ingress_class()

    data = {
        "hostname":hostname,
        "route_name":"openwhisk-route",
        "tls":tls,
        "ingress_name":"openwhisk-route",
        "service_name":"controller-ip",
        "service_kind":"Service",
        "service_port":"8080",
        "context_path":"/",
        "static_ingress": False
    }

    return data    

def create_osh_route_spec(data):
    tpl = "generic-openshift-route-tpl.yaml"
    logging.info(f"*** Configuring host {data['hostname']} endpoint for openwhisk controller using {tpl}")
    return kus.processTemplate("openwhisk-endpoint", tpl, data)

def create_ingress_route_spec(data):
    tpl = "generic-ingress-tpl.yaml"
    logging.info(f"*** Configuring host {data['hostname']} endpoint for openwhisk controller using {tpl}")
    return kus.processTemplate("openwhisk-endpoint", tpl, data)    

def create(owner=None):
    runtime = cfg.get('nuvolaris.kube')
    tls = cfg.get('components.tls')
    
    apihost = apihost_util.get_apihost(runtime)
    logging.info(f"*** Saving configuration for OpenWishk apihost={apihost}")
    openwhisk.annotate(f"apihost={apihost}")
    cfg.put("config.apihost", apihost)

    data = runtime=='openshift' and get_osh_data(apihost, tls) or get_ingress_data(apihost, tls)
    spec = runtime=='openshift' and create_osh_route_spec(data) or create_ingress_route_spec(data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.endpoint.spec", spec)
        
    return kube.apply(spec)
    
def delete_by_owner():
    runtime = cfg.get('nuvolaris.kube')
    tpl = runtime=='openshift' and "_generic-openshift-route-tpl.yaml" or "_generic-ingress-tpl.yaml"
    res = kube.kubectl("delete", "-f", f"deploy/openwhisk-endpoint/{tpl}")
    logging.info(f"delete endpoint: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.endpoint.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        return res

def delete(owner=None):
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()

def patch(status, action, owner=None):
    """
    Called the the operator patcher to create/delete endpoint for apihost
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
        logging.info(f"*** hanlded request to {action} endpoint") 
    except Exception as e:
        logging.error('*** failed to update endpoint: %s' % e)
        status['whisk_create']['endpoint']='error'                       
