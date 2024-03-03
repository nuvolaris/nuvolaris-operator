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
import nuvolaris.openwhisk as openwhisk
import nuvolaris.kube as kube
import nuvolaris.userdb_util as userdb
import nuvolaris.config as cfg
import nuvolaris.util as ut
import nuvolaris.whisk_actions_deployer as system
import nuvolaris.redis as redis

from nuvolaris.nuvolaris_metadata import NuvolarisMetadata

def annotate_operator_components_version():
    """
    This functions scans for pod matching the annotations whisks.nuvolaris.org/annotate-version: "true"
    and uses pod metadata.labels.name and spec.containers.image to annotate the global config map cm/config
    """
    try:
        logging.info("**** annotating nuvolaris operator component versions")
        pods = kube.kubectl("get","pods",jsonpath="{.items[?(@.metadata.annotations.whisks\.nuvolaris\.org\/annotate-version)]}",debugresult=False)

        for pod in pods:
            if(pod['metadata'].get('labels') and pod['metadata']['labels'].get('name')):
                pod_name = pod['metadata']['labels']['name']
                pod_image = pod['spec']['containers'][0]['image']

                if(pod_name):
                    openwhisk.annotate(f"{pod_name}_version={pod_image}")
            else:
                logging.warn("**** found a pod with whisks.nuvolaris.org/annotate-version without metadata.labels.name attribute")
                logging.warn(pod)
        
        logging.info("**** completed annotation of nuvolaris operator component versions")       
    except Exception as e:
        logging.error(e)

def update_nuvolaris_metadata():
    try:
        logging.info("**** persisting nuvolaris metadata")
        nuv_metadata = NuvolarisMetadata()
        nuv_metadata.dump()
        userdb.save_nuvolaris_metadata(nuv_metadata)
        logging.info("**** nuvolaris metadata successfully persisted")
    except Exception as e:
        logging.error(e)        

def whisk_post_create(name):
    """
    Executes a set of common operations after the operator terminated the deployment process.
    - persists nuvolaris metadata into the internal couchdb
    - annotate operator deployed components version
    - deploys system actions
    """
    logging.info(f"*** whisk_post_create {name}")
    update_nuvolaris_metadata()
    annotate_operator_components_version()
    return system.deploy_whisk_system_action()

def whisk_post_resume(name):
    """    
    Executes a set of common operations after the operator resumes, which is also the scenario
    triggered by a nuv update operator
    - restore redis nuvolaris namespace if redis is active
    - annotate operator deployed components version
    - redeploys system actions
    """
    logging.info(f"*** whisk_post_resume {name}")

    if cfg.get("components.redis"):
        redis.restore_nuvolaris_db_user()

    annotate_operator_components_version()
    sysres = system.deploy_whisk_system_action()

    if sysres:
        logging.info("system action redeployed after operator restart")
    else:    
        logging.warn("system action deploy issues after operator restart. Checl logs for further details")

def config_from_spec(spec, handler_type = "on_create"):
    """
    Initialize the global configuration from the given spec.
    :param spec 
    :param on_resume boolen flag telling if thsi method is called from the on_resume handler
    """
    cfg.clean()
    cfg.configure(spec)
    cfg.detect()

    if "on_create" in handler_type:       
        cfg.put("config.apihost", "https://pending")
        logging.debug("**** dumping initial configuration")

    if "on_update" in handler_type:               
        logging.debug("**** dumping updated configuration")        

    if "on_resume" in handler_type:
        apihost = ut.get_apihost_from_config_map()
        cfg.put("config.apihost", apihost)
        logging.debug("**** dumping resumed configuration")        

    cfg.dump_config()