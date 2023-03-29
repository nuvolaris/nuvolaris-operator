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
import json, flatdict, os, os.path
import yaml
import nuvolaris.config as cfg
import nuvolaris.kube as kube
import nuvolaris.template as tpl

# tested by an integration test
@kopf.on.login()
def login(**kwargs):
    token = '/var/run/secrets/kubernetes.io/serviceaccount/token'
    if os.path.isfile(token):
        logging.debug("found serviceaccount token: login via pykube in kubernetes")
        return kopf.login_via_pykube(**kwargs)
    logging.debug("login via client")
    return kopf.login_via_client(**kwargs)

# tested by an integration test
@kopf.on.create('nuvolaris.org', 'v1', 'workflows')
def workflows_create(spec, name, **kwargs):
    logging.info(f"*** workflows_create {name}")

    whisk = dict(kube.kubectl('get', 'whisk', 'controller', namespace='nuvolaris', jsonpath='{.spec}')[0])
    cfg.clean()
    cfg.configure(whisk)
    cfg.detect()
    cfg.dump_config()
    data = {
        'name': '',
        'apihost': cfg.get('nuvolaris.apihost'),
        'auth': cfg.get('openwhisk.namespaces.nuvolaris'),
        'args': [],
        'image': 'ghcr.io/fsilletti/wfm:0.2'
    }

    for w in spec.get('workflows'):
        argsK8s = []
        for a in list(w.get('parameters').keys()):
            arg = a + '=' + str(w.get('parameters').get(a))
            argsK8s.append(arg)

        data['name'] = w.get('name')
        data['args'] = argsK8s
        obj = tpl.expand_template('workflow-job.yaml', data)
        print(obj)
        kube.apply(obj)
