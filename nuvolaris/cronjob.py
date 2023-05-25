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
import kopf, logging, json
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg

def create(owner=None):
    logging.info("creating cron")
    
    img = cfg.get('operator.image') or "missing-operator-image"
    tag = cfg.get('operator.tag') or "missing-operator-tag"
    image = f"{img}:{tag}"
    logging.info(f"cron using image {image}")

    #default to every minutes if not configured
    schedule = cfg.get('scheduler.schedule') or "* * * * *"
    config = {
        "scheduler.schedule":schedule,
        "controller.protocol":cfg.get('controller.protocol') or "http",
        "controller.host":cfg.get('controller.host') or "controller",
        "controller.port":cfg.get('controller.port') or "3233",
        "couchdb.controller.user":cfg.get('couchdb.controller.user'),
        "couchdb.controller.password":cfg.get('couchdb.controller.password')
    }

    data = {
        "image": image,
        "schedule": schedule,
        "config": json.dumps(config),
        "name": "cron"
    }
    
    kust = kus.patchTemplate("scheduler", "cron-init.yaml", data)    
    spec = kus.kustom_list("scheduler", kust, templates=[], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.cron.spec", spec)

    res = kube.apply(spec)
    logging.info(f"create cron: {res}")
    return res    

def delete_by_owner():
    spec = kus.build("scheduler")
    res = kube.delete(spec)
    logging.info(f"delete cron: {res}")
    return res

def delete_by_spec():
    spec = cfg.get("state.cron.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete cron: {res}")
    return res

def delete(owner=None):
    if owner:        
        return delete_by_owner()
    else:
        return delete_by_spec()

def patch(status, action, owner=None):
    """
    Called the the operator patcher to create/delete cron component
    """
    try:
        logging.info(f"*** handling request to {action} cron")  
        if  action == 'create':
            msg = create(owner)
            status['whisk_create']['cron']='on'
        else:
            msg = delete(owner)
            status['whisk_create']['cron']='off'

        logging.info(msg)        
        logging.info(f"*** hanlded request to {action} cron") 
    except Exception as e:
        logging.error('*** failed to update cron: %s' % e)
        status['whisk_create']['cron']='error'       