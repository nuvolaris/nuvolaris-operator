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
# this module wraps utilities functions
import nuvolaris.kube as kube
import logging


# get the default storage class defined on the configured kubernetes environment
def get_default_storage_class():
    storage_class = kube.kubectl("get", "storageclass", jsonpath="{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io\/is-default-class)].metadata.name}")
    if(storage_class):
        return storage_class[0]

    return ""

# get the default storage provisioner defined on the configured kubernetes environment
def get_default_storage_provisioner():
    storage_class = kube.kubectl("get", "storageclass", jsonpath="{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io\/is-default-class)].provisioner}")
    if(storage_class):
        return storage_class[0]

    return ""

# determine the ingress-nginx flavour
def get_ingress_namespace(runtime):
    if runtime == "microk8s":
        return "ingress" 
    else:
        return  "ingress-nginx"

# determine the ingress-nginx flavour
def get_ingress_yaml(runtime):
    if runtime == "eks":
        return "eks-nginx-ingress.yaml"
    elif runtime == "kind":
        return  "kind-nginx-ingress.yaml"  
    else:
        return  "cloud-nginx-ingress.yaml"            