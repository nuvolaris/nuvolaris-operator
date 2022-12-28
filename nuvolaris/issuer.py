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
import kopf, logging, json
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import time

def get_cm_pod_name(runtime, jpath, namespace="cert-manager"):
    # pod_name is retuned as a string array
    pod_name = kube.kubectl("get", "pods", namespace=namespace, jsonpath=jpath)
    if pod_name:
        return pod_name[0]
    
    return None

def wait_for_cm_ready(runtime, jpath, namespace="cert-manager"):
    pod_name = get_cm_pod_name(runtime, jpath, namespace)

    if pod_name:
        logging.info(f"checking for {pod_name}")
        while not kube.wait(f"pod/{pod_name}", "condition=ready",namespace=namespace):
            logging.info(f"waiting for {pod_name} to be ready...")
            time.sleep(1)
    else:
        logging.error("*** could not determine if cert-manager webhook pod is up and running")

def create(owner=None):
    logging.info(f"*** Configuring cluster issuer")
    # We deploy a cluster-issuer
    runtime = cfg.get('nuvolaris.kube')
    acme_registered_email = cfg.get('tls.acme-registered-email') or "nuvolaris@nuvolaris.io"
    acme_server_url = cfg.get('tls.acme-server-url') or "https://acme-staging-v02.api.letsencrypt.org/directory"

    # ensure the cert-manager pods are running
    webhook_path = "{.items[?(@.metadata.labels.app\.kubernetes\.io\/component == 'webhook')].metadata.name}"
    controller_path = "{.items[?(@.metadata.labels.app\.kubernetes\.io\/component == 'controller')].metadata.name}"
    cainjector_path = "{.items[?(@.metadata.labels.app\.kubernetes\.io\/component == 'cainjector')].metadata.name}"
    
    wait_for_cm_ready(runtime, controller_path)
    wait_for_cm_ready(runtime, cainjector_path)
    wait_for_cm_ready(runtime, webhook_path)

    # wait for a minute before creating the issuer
    logging.info("*** waiting 60 seconds before creating a cluster issuer")
    time.sleep(60)

    # On microk8s cluster issuer class must be public
    issuer_class = runtime == "microk8s" and "public" or "nginx"
    
    logging.info(f"*** Configuring cluster issuer using email {acme_registered_email}")
    logging.info(f"*** Configuring cluster issuer using let's encrypt server {acme_server_url}")
  
    data = {
        "acme_registered_email": acme_registered_email,
        "acme_server_url": acme_server_url,
        "issuer_class":issuer_class,
        "name": "tls"
    }
    
    kust = kus.patchTemplate("issuer", "cluster-issuer.yaml", data)
    spec = "deploy/issuer/__cluster-issuer.yaml"

    cfg.put("state.issuer.spec", spec)
    res = kube.kubectl("apply", "-f", spec,namespace=None)
    return res

def delete():
    spec = cfg.get("state.issuer.spec")
    res = False
    if spec:
        res = kube.kubectl("delete", "-f", spec,namespace=None)
        return res

