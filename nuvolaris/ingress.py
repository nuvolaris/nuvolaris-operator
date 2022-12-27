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

def get_ingress_pod_name(runtime, namespace="ingress-nginx"):
    jpath = "{.items[?(@.metadata.labels.app\.kubernetes\.io\/component == 'controller')].metadata.name}"

    if runtime == "microk8s":
         jpath= "{.items[?(@.metadata.labels.name == 'nginx-ingress-microk8s')].metadata.name}"

    # pod_name is retuned as a string array
    pod_name = kube.kubectl("get", "pods", namespace=namespace, jsonpath=jpath)
    if pod_name:
        return pod_name[0]
    
    return None

def wait_for_ingress_ready(runtime, namespace="ingress-nginx"):
    pod_name = get_ingress_pod_name(runtime, namespace)

    if pod_name:
        logging.info(f"checking for {pod_name}")
        while not kube.wait(f"pod/{pod_name}", "condition=ready",namespace=namespace):
            logging.info(f"waiting for {pod_name} to be ready...")
            time.sleep(1)
    else:
        logging.error("*** could not determine if ingress-nginx pod is up and running")

# determine the ingress-nginx flavour
def get_ingress_yaml(runtime):
    if runtime == "eks":
        return "eks-nginx-ingress.yaml"
    elif runtime == "kind":
        return  "kind-nginx-ingress.yaml"  
    else:
        return  "cloud-nginx-ingress.yaml"

# determine the ingress-nginx flavour
def get_ingress_namespace(runtime):
    if runtime == "microk8s":
        return "ingress" 
    else:
        return  "ingress-nginx"    

# determine the ingress-nginx flavour
def get_ingress_service(runtime):
    return "service/ingress-nginx-controller"

def create(owner=None): 
    runtime = cfg.get('nuvolaris.kube')
    namespace = get_ingress_namespace(runtime)
    service = get_ingress_service(runtime)

    if(runtime == "microk8s"):
        logging.info("*** checking availability of microk82 ingressa addon")
        pod_name = get_ingress_pod_name(runtime, namespace)

        if pod_name:
            return f"*** ingress-nginx {pod_name} already installed...skipping setup"
        else:
            # TODO find a way to setup the standard ingress-nginx also on microk8s. For the moment we ask to enable it.
            return "*** microk8s ingress missing. Enable it using microk8s enable ingress on your cluster"
    else:
        ingress = kube.get(service,namespace)
        if ingress:
            return "*** ingress-nginx already installed...skipping setup"

    ingress_yaml = get_ingress_yaml(runtime)
    logging.info(f"*** Configuring ingress-nginx {ingress_yaml}")

    # we apply the ingress specs as they are
    spec_setup = f"deploy/ingress-nginx/operator-ingress-setup.yaml"
    spec = f"deploy/ingress-nginx/{ingress_yaml}"
    cfg.put("state.ingress.spec", spec)
    cfg.put("state.ingress.spec_setup", spec_setup)

    res = kube.kubectl("apply", "-f", spec_setup, namespace=None)        
    res = kube.kubectl("apply", "-f", spec, namespace=None)

    #we need to be sure that the ingress is ready
    wait_for_ingress_ready(runtime, namespace)
    return res

def delete():
    spec = cfg.get("state.ingress.spec")
    spec_setup = cfg.get("state.ingress.spec_setup")
    res = False
    if spec:
        res = kube.kubectl("delete", "-f", spec, namespace=None)
        res = kube.kubectl("delete", "-f", spec_setup, namespace=None)
        return res