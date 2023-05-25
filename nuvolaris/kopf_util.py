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
import json, logging

def normalize(item:tuple):
    """
    Takes a kopf diff tuple and normalize it by concatenating the modified element into a path attribute
    >>> item = ('change', ('spec','component','tls'), 'true', 'false')
    >>> print(normalize(item))
    {'path': 'spec.component.tls', 'action': 'change', 'old': 'true', 'new': 'false'}
    """
    res = {}    
    path = ""
    for path_element in item[1]:
        path = f"{path}{path_element}."
    
    res['path']=path[:-1]
    res['action']=item[0]
    res['old']=item[2]
    res['new']=item[3]

    return res

def endpoint(response: dict, item: dict):
    """
    Forces an update of the apihost endpoint if any of these two attributes has been changed/added
    """
    if(item['path']=='spec.components.tls' or item['path']=='spec.nuvolaris.apihost'):
        response["endpoint"]="update"

def openwhisk(response: dict, item: dict):
    """
    Forces an update of Openwhisk if a change in the global spec.config has been detected.
    This will force the redeploy of the Openwhisk controller/invoker where supported
    """
    if item['path'].find('spec.configs') >= 0:
        response["openwhisk"]="update" 

def check_component(response: dict, item: dict, cmp_spec, cmp_key):
    """
    Check if the componet identified by cmp_spec has been enabled or disabled
    """
    if item['path'].find(cmp_spec) > -1:
        if(item['new']):
            response[cmp_key]="create"
        else: 
            response[cmp_key]="delete"       

def evaluate_differences(response: dict, differences: list):
    """
    Iterate over the difference list to find which components the
    nuvolaris operator need to deploy/undeploy
    """
    for d in differences:
        check_component(response, d,"spec.components.couchdb","couchdb")
        check_component(response, d,"spec.components.mongodb","mongodb")
        check_component(response, d,"spec.components.kafka","kafka")
        check_component(response, d,"spec.components.zookeeper","zookeeper")
        check_component(response, d,"spec.components.redis","redis")
        check_component(response, d,"spec.components.cron","cron")
        check_component(response, d,"spec.components.minio","minio")
        check_component(response, d,"spec.components.static","static") 
        check_component(response, d,"spec.components.postgres","postgres")
        openwhisk(response, d)           
        endpoint(response, d)
        
def detect_component_changes(kopf_diff):
    """
    Analyze a kopf diff object and attempt to establish which component must be added/removed/updated by the operator.
    Typically a kopf diff object has a structure like ((action, n-tuple of object or field path, old, new),)
    Will return a list of items reporting the specific action to be done on any nuvolaris operator managed component
    >>> data = (('change',('spec','components','mongodb'), True, False),('change',('spec','components','tls'), True, False),('change', ('spec','configs','limits','actions','sequence-maxLength'), 10, 20))
    >>> what_to_do = detect_component_changes(data)
    >>> print(what_to_do['endpoint'])
    update
    >>> print(what_to_do['openwhisk'])    
    update
    >>> print(what_to_do['mongodb'])        
    delete
    """
    differences = list()
    for t in kopf_diff:
        logging.info(f"*** processing difference {t}")
        differences.append(normalize(t))

    response = {}
    evaluate_differences(response, differences)

    return response