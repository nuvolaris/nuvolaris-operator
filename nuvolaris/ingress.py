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

def get_ingress_pod_name():
    # pod_name is retuned as a string array
    pod_name = kube.kubectl("get", "pods", namespace="ingress-nginx", jsonpath="{.items[?(@.metadata.labels.app\.kubernetes\.io\/component == 'controller')].metadata.name}")
    if pod_name:
        return pod_name[0]
    
    return None

def wait_for_ingress_ready():
    pod_name = get_ingress_pod_name()

    if pod_name:
        logging.info(f"checking for {pod_name}")
        while not kube.wait(f"pod/{pod_name}", "condition=ready",namespace="ingress-nginx"):
            logging.info(f"waiting for {pod_name} to be ready...")
            time.sleep(1)
    else:
        logging.error("*** could not determine if ingress-nginx pod is up and running")

def get_ingress_yaml():
    runtime = cfg.get('nuvolaris.kube')
    return runtime == "eks" and "eks-nginx-ingress.yaml" or "generic-nginx-ingress.yaml"

def create(owner=None):
    ingress = kube.get("service/ingress-nginx-controller","ingress-nginx")
    if ingress:
        return "*** ingress-nginx already installed...skipping setup"
    else:
        ingress_yaml = get_ingress_yaml()
        logging.info(f"*** Configuring ingress-nginx {ingress_yaml}")

        # we apply the ingress specs as they are
        spec = kus.raw("ingress-nginx",ingress_yaml)
        cfg.put("state.ingress.spec", spec)        
        res = kube.kubectl("apply", "-f", f"deploy/ingress-nginx/{ingress_yaml}",namespace=None)

        #we need to be sure that the ingress is ready
        wait_for_ingress_ready()
        return res

def delete():
    spec = cfg.get("state.ingress.spec")
    res = False
    ingress_yaml = get_ingress_yaml()
    if spec:
        res = kube.kubectl("delete", "-f", f"deploy/ingress-nginx/{ingress_yaml}",namespace=None)
        return res