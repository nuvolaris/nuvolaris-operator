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
# wsk project deploy --project deploy/whisk-system —-apihost http://localhost:3233 --auth 789c46b1-71f6-4ed5-8c54-816aa4f8c502:abczO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP
#

import logging
import json
import nuvolaris.config as cfg
import nuvolaris.template as ntp
import nuvolaris.util as util
import nuvolaris.kustomize as kust
import os

from nuvolaris.whisk_system_util import WhiskSystemClient
from nuvolaris.util import nuv_retry
from subprocess import CompletedProcess

def get_couchdb_inputs():
    couchdb_host = cfg.get("couchdb.host") or "couchdb"
    couchdb_port = cfg.get("couchdb.port") or "5984"

    cdb_inputs=[]
    cdb_inputs.append({"key":"couchdb_user", "value":cfg.get("couchdb.admin.user", "COUCHDB_ADMIN_USER", "whisk_admin")})
    cdb_inputs.append({"key":"couchdb_password", "value":cfg.get("couchdb.admin.password", "COUCHDB_ADMIN_PASSWORD", "some_passw0rd")})
    cdb_inputs.append({"key":"couchdb_host", "value":couchdb_host})
    cdb_inputs.append({"key":"couchdb_port", "value":couchdb_port})

    return cdb_inputs

def prepare_login_action():
    login = {
        "name":"login",
        "function":"login.zip",
        "runtime":"python:3",
        "web":"true",
        "inputs":get_couchdb_inputs()
    }

    return login

def prepare_content_action():
    minio_host= cfg.get("minio.host") or "minio"
    minio_port= cfg.get("minio.port") or "9000"
    minio_full_host = f"{minio_host}.nuvolaris.svc.cluster.local"

    content_inputs=[]
    content_inputs.append({"key":"minio_host", "value":minio_full_host})
    content_inputs.append({"key":"minio_port", "value":minio_port})    

    content = {
        "name":"content",
        "function":"content.zip",
        "runtime":"python:3",
        "web":"true",
        "inputs":content_inputs
    }

    return content 

def prepare_redis_action():

    redis = {
        "name":"redis",
        "function":"redis.zip",
        "runtime":"python:3",
        "web":"raw",
        "inputs":get_couchdb_inputs()
    }

    return redis 

def prepare_psql_action():
    psql = {
        "name":"psql",
        "function":"psql.zip",
        "runtime":"python:3",
        "web":"raw",
        "inputs":get_couchdb_inputs()
    }

    return psql  

def prepare_minio_action():
    minio = {
        "name":"minio",
        "function":"minio.zip",
        "runtime":"python:3",
        "web":"raw",
        "inputs":get_couchdb_inputs()
    }

    return minio  

def prepare_dev_upload_action():
    dev_upload = {
        "name":"devel_upload",
        "function":"devel_upload.zip",
        "runtime":"python:3",
        "web":"raw",
        "inputs":get_couchdb_inputs()
    }

    return dev_upload  

def prepare_ferretdb_action():
    ferretdb = {
        "name":"ferretdb",
        "function":"ferretdb.zip",
        "runtime":"python:3",
        "web":"raw",
        "inputs":get_couchdb_inputs()
    }

    return ferretdb 

def prepare_dev_download_action():
    dev_download = {
        "name":"devel_download",
        "function":"devel_download.zip",
        "runtime":"python:3",
        "web":"raw",
        "inputs":get_couchdb_inputs()
    }

    return dev_download             


def prepare_system_actions():
    """ Builds a suitable structure to generate a deployment manifest using a template
    """
    actions = []
    actions.append(prepare_login_action())
    actions.append(prepare_content_action())
    actions.append(prepare_redis_action())
    actions.append(prepare_psql_action())
    actions.append(prepare_minio_action())
    actions.append(prepare_dev_upload_action())
    actions.append(prepare_ferretdb_action())
    actions.append(prepare_dev_download_action())
    return {"actions":actions}

def process_wsk_result(result: CompletedProcess, expected_success_msg: str):
    """
    Parses a subprocess.CompletedProcess object and raises an exception if the
    returncode != 0 or the stdout response does not contains the expected message.
    Raising an Exception forces a retry if the @nuv_retry decorator is used.
    """
    has_error = False
    logging.debug(f"expected message for success {expected_success_msg}")

    returncode = result.returncode
    output = result.stdout.decode()
    error = result.stderr.decode()

    if returncode != 0:
        logging.warn(f"error {error} detected when deploying system action")
        has_error = True

    if not expected_success_msg in output:
        logging.warn(f"response {output} does not contains the expected result {expected_success_msg}")
        has_error = True

    if has_error:
        logging.warn(f"could not validate wsk response {result}")
        raise Exception("whisk system action deployement failure. Forcing a retry")

    logging.info(f"successfully validated wsk response {result}")

@nuv_retry()
def safe_deploy(wskClient):
    logging.info("*** deploying deploy/whisk-system project")

    deployProjectResponse = wskClient.wsk("project","deploy","--project","deploy/whisk-system")
    process_wsk_result(deployProjectResponse, "Success")

    actionListResult = wskClient.wsk("action","list") 
    process_wsk_result(actionListResult, "whisk-system/nuv/login")

    return True

def deploy_whisk_system_action():
    try:
        auth = cfg.get('openwhisk.namespaces.whisk-system')
        data = prepare_system_actions()
        tplres = kust.processTemplate("whisk-system","whisk-system-manifest-tpl.yaml",data,"manifest.yaml")

        wskClient = WhiskSystemClient(auth)
        result = safe_deploy(wskClient)
        return result
    except Exception as e:
        logging.error("Error detected when deploying system actions", e)
