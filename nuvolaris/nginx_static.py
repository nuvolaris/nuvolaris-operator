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

def create(owner=None):
    logging.info(f"*** configuring nuvolaris nginx static provider")

    data = {
        "minio_host": cfg.get('minio.host') or "minio",
        "minio_post": cfg.get('minio.port') or "9000",
    }
    
    kust = kus.patchTemplates("nginx-static", ["nginx-static-cm.yaml","nginx-static-dep.yaml"], data)    
    spec = kus.kustom_list("nginx-static", kust, templates=[], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.ngix-static.spec", spec)

    res = kube.apply(spec)

    logging.info("*** configured nuvolaris nginx static provider")
    return res

def delete():
    spec = cfg.get("state.ngix-static.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete nuvolaris nginx static provider: {res}")
    return res

def static_ingress_name(namespace):
    return f"{namespace}-static-ingress"

def static_secret_name(namespace):
    return f"{namespace}-static-secret"

def render_ingress_template(namespace,template,data):
    """
    uses the given template policy to render a final ingress template.
    """  
    out = f"/tmp/__{namespace}_{template}"
    file = ntp.spool_template(template, out, data)
    return os.path.abspath(file)      

def create_ow_static_endpoint(ucfg, owner=None):
    namespace = ucfg.get("namespace")
    logging.info(f"*** configuring static endpoint for {namespace}")

    runtime = cfg.get('nuvolaris.kube')
    host = ucfg.get('object-storage.route.host')
    bucket = ucfg.get('object-storage.route.bucket')
    tls = cfg.get('components.tls') and not runtime=='kind'
    ingress_class = cfg.detect_ingress_class()
    context_path = tls and "/" or f"/{bucket}"

    data = {
        "namespace":namespace,
        "ingress_name": static_ingress_name(namespace),
        "secret_name": static_secret_name(namespace),
        "ingress_class": ingress_class,
        "tls": tls,
        "hostname": host,        
        "rewrite_target":f"/{bucket}/$1",
        "nginx_static_service": "nuvolaris-static-svc",
        "nginx_static_service_port": 80,
        "context_path":context_path
    }

    try:
        path_to_template_yaml = render_ingress_template(namespace,"static-ingress-tpl.yaml",data)
        res = kube.kubectl("apply", "-f",path_to_template_yaml)
        os.remove(path_to_template_yaml)
        return res
    except Exception as e:
        logging.warn(e)       
        return False

def delete_ow_static_endpoint(ucfg):
    namespace = ucfg.get("namespace")
    logging.info(f"*** removing static endpoint for {namespace}")
    
    try:
        ingress_name = static_ingress_name(namespace)
        return kube.kubectl("delete", "ingress",ingress_name)
    except Exception as e:
        logging.warn(e)       
        return False           
