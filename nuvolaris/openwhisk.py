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
import nuvolaris.config as cfg
import nuvolaris.openwhisk_standalone as standalone
import nuvolaris.kube as kube
import urllib.parse
import os, os.path
import logging

# this functions returns the apihost to be stored as annotation
def apihost(apiHost):
    logging.info(f"*** openwhisk received ingress {apiHost}")
    runtime = cfg.get('nuvolaris.kube')
    url = urllib.parse.urlparse("https://pending")

    if apiHost and len(apiHost) > 0: 
        if "hostname" in apiHost[0]:
            url = url._replace(netloc = apiHost[0]['hostname'])
        elif "ip" in apiHost[0]:
            url = url._replace(netloc = apiHost[0]['ip'])

    if cfg.exists("nuvolaris.apihost"):
        url =  url._replace(netloc = cfg.get("nuvolaris.apihost"))
    if cfg.exists("nuvolaris.protocol"):
        url = url._replace(scheme = cfg.get("nuvolaris.protocol"))
    if cfg.exists("nuvolaris.apiport"):
        url = url._replace(netloc = f"{url.hostname}:{cfg.get('nuvolaris.apiport')}")

    # overrides the protocols in case tls is enabled
    if cfg.get('components.tls') and not runtime=="kind":
        url = url._replace(scheme = "https")
    else:
        url = url._replace(scheme = "http")    

    return url.geturl()

def annotate(keyval):
    kube.kubectl("annotate", "cm/config",  keyval, "--overwrite")

def create(owner=None):
    useInvoker = cfg.get('components.invoker') or False
    
    if not useInvoker:
        logging.info("*** creating openwhisk in standalone mode") 
        return standalone.create(owner)

def delete():
    useInvoker = cfg.get('components.invoker') or False

    if not useInvoker:
        return standalone.delete()    
