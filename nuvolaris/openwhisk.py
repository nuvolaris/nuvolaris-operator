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
import logging
import nuvolaris.config as cfg
import nuvolaris.openwhisk_standalone as standalone
import nuvolaris.kube as kube
import nuvolaris.util as util
from nuvolaris.util import nuv_retry

@nuv_retry()
def annotate(keyval):
    kube.kubectl("annotate", "cm/config",  keyval, "--overwrite")

def create(owner=None):
    # openwhisk controller relies on couchdb therefore we wait for pod readiness
    util.wait_for_pod_ready("{.items[?(@.metadata.labels.name == 'couchdb')].metadata.name}")

    useInvoker = cfg.get('components.invoker') or False
    
    if not useInvoker:
        logging.info("*** creating openwhisk in standalone mode") 
        return standalone.create(owner)

def delete():
    useInvoker = cfg.get('components.invoker') or False

    if not useInvoker:
        return standalone.delete()    
