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
import kopf
import logging
import platform
import os, os.path
import nuvolaris.kube as kube
import nuvolaris.openwhisk as openwhisk
import nuvolaris.bucket as bucket
import requests as req
import yaml
import json
import uuid
from datetime import datetime

SLACK_URL = 'https://hooks.slack.com/services/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'
TOKEN = '/var/run/secrets/kubernetes.io/serviceaccount/token'
SECRETS_PATH = "nuvolaris-test/tests/operator-obj.yaml"
SECRETS = yaml.safe_load(open(SECRETS_PATH))["spec"]
LOGIN_TEXTS = {'client' : 'logged in via client', 'pykube' : 'logged in via pykube in kubernetes'}    
UUID = uuid.uuid4()

def get_notification_header(type):
    return f'[{datetime.now()}] #{type} #openwhisk #monitor #operator #notification #Y{datetime.now().year} #M{datetime.now().month} #D{datetime.now().day} #H{datetime.now().hour} #{UUID.hex}'

def get_system_info():
    return f'{platform.system()} - {platform.machine()} - {platform.architecture()}'

def get_login_notification(json):
    if os.path.isfile(TOKEN):
        login_text = LOGIN_TEXTS['pykube']  
    else:
        login_text = LOGIN_TEXTS['client']
    return f'{get_notification_header("login")}\n- OpenWhisk Monitor Operator {login_text} from: {get_system_info()}\n- Operator ID: {UUID.hex}\n- Pods at {datetime.now()}:\n{json}'

def get_creation_notification(json, message):
    return f'{get_notification_header("create")}\n- OpenWhisk Created!\n- Info:\n{message}\n- Pods at {datetime.now()}:\n{json}'

def get_deletion_notification(json, message):
    return f'{get_notification_header("delete")}\n- OpenWhisk Deleted!\n- Info:\n{message}\n- Pods at {datetime.now()}:\n{json}'

def get_logout_notification():
    return f'{get_notification_header("logout")}\n- OpenWhisk Monitor Operator logged out from: {get_system_info()}\n- Operator ID: {UUID.hex}'

def get_status_notification(message):
    return f'{get_notification_header("status")}\n- OpenWhisk Status Changed!\n- Info:\n{message}'
def get_pods_json():
    try:
        pods = kube.kubectl("get", "pods", jsonpath='{.items[]}')  
    except:
        return 'No pods responded'
    
    pods_json_dump = json.dumps(pods, indent=4, sort_keys=True)
    return pods_json_dump.replace('\\"', '"')

# tested by an integration test
@kopf.on.login()
def login(**kwargs):
    req.post(
        SLACK_URL, 
        json={
        'text' : get_login_notification(get_pods_json())
    })
    
    if os.path.isfile(TOKEN):
        logging.debug("found serviceaccount token: login via pykube in kubernetes")
        return kopf.login_via_pykube(**kwargs)

    return kopf.login_via_client(**kwargs)

# tested by an integration test
@kopf.on.create('nuvolaris.org', 'v1', 'whisks')
def whisk_create(spec, name, **kwargs):
    message = []
    message.append(openwhisk.create())
    msg = "\n".join(message)
    logging.debug(msg)
    req.post(
        SLACK_URL, 
        json={
            'text' : get_creation_notification(get_pods_json(), msg)
        }
    )
    return msg

# tested by an integration test
@kopf.on.delete('nuvolaris.org', 'v1', 'whisks')
def whisk_delete(spec, **kwargs):
    message = []
    try:
        message.append('- DELETION RESULT: ' + openwhisk.delete())
    except:
        message.append('- DELETION RESULT: Failed to delete OpenWhisk deployment.\n')

    try:
        message.append('- CLEANUP RESULT: ' + openwhisk.cleanup())
    except:
        message.append('- CLEANUP RESULT: Failed clean-up of OpenWhisk deployment.\n')

    msg = "\n".join(message)
    logging.debug(msg)
    req.post(
        SLACK_URL, 
        json={
            'text' : get_deletion_notification(get_pods_json(), msg)
        }
    )
    return msg

@kopf.on.cleanup()
def logout(**kwargs):
    req.post(
        SLACK_URL, 
        json={
            'text' : get_logout_notification()
        }
    )

# tested by integration test
@kopf.on.field("service", field='status.loadBalancer')
def service_update(old, new, name, **kwargs):
    node_labels = kube.kubectl("get", "nodes", jsonpath='{.items[].metadata.labels}')
    ingress = []
    if "ingress" in new and len(new['ingress']) >0:
        ingress = new['ingress']   
    apihost = openwhisk.apihost(ingress, node_labels)
    req.post(
        SLACK_URL, 
        json={
            'text' : get_status_notification(f'- apihost: {apihost}\n- name: {name}\n- new: {new}\n- old: {old}')
        }
    )
    openwhisk.annotate(f"apihost={apihost}")