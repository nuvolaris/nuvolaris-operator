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
import logging, time
import nuvolaris.openwhisk as openwhisk
import nuvolaris.config as cfg
import nuvolaris.kube as kube
import nuvolaris.util as util

def restart_sts(sts_name):
    try:
        replicas =  1
        current_rep = kube.kubectl("get",sts_name,jsonpath="{.spec.replicas}")
        if current_rep:
            replicas = current_rep[0]
        
        kube.scale_sts(sts_name,0)
        time.sleep(5)
        logging.info(f"scaling {sts_name} to {replicas}")
        kube.scale_sts(sts_name,replicas)
    except Exception as e:
        logging.error('failed to scale up/down %s: %s' % sts_name,e)

def redeploy_controller(owner=None):
    try:
        msg = openwhisk.delete()
        logging.info(msg)

        msg = openwhisk.create(owner)
        logging.info(msg)
    except Exception as e:
        logging.error('failed to redeploy openwhisk controller: %s' % e)  

def restart_whisk():
    logging.info("*** handling request to redeploy whisk controller using scaledown/scaleup")
    restart_sts("sts/controller")
    logging.info("*** handling request to redeploy whisk controller using scaledown/scaleup")

def redeploy_whisk(owner=None):
    logging.info("*** handling request to redeploy whisk controller")
    redeploy_controller(owner)
    logging.info("*** handled request to redeploy whisk controller")
