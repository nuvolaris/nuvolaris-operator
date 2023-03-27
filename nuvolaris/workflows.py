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
    jobTemplateRaw = """
    apiVersion: batch/v1
    kind: Job
    metadata:
      name: ""
    spec:
      ttlSecondsAfterFinished: 100
      template:
        spec:
          containers:
            - name: ""
              image: default-route-openshift-image-registry.apps.wfx.sciabarra.net/paas-images/wfm:0.2
              env:
                - name: APIHOST
                  value: ""
                - name: AUTH
                  value: ""
              args: []
          restartPolicy: OnFailure
    """

    whisk = dict(kube.kubectl('get', 'whisk', 'controller', namespace='nuvolaris', jsonpath='{.spec}')[0])
    cfg.clean()
    cfg.configure(whisk)
    cfg.detect()
    cfg.dump_config()
    auth = cfg.get('openwhisk.namespaces.nuvolaris')
    apihost= cfg.get('nuvolaris.apihost')
    jobFile = ''

    for w in spec['workflows']:
        jobTeplate = yaml.safe_load(jobTemplateRaw)
        jobTeplate['metadata']['name'] = name
        jobContainerTeplate = jobTeplate['spec']['template']['spec']['containers'][0]
        jobContainerTeplate['name'] = name

        if jobContainerTeplate['env'][0]['name'] == 'APIHOST':
            jobContainerTeplate['env'][0]['value'] = apihost
            jobContainerTeplate['env'][1]['value'] = auth
        else:
            jobContainerTeplate['env'][0]['value'] = auth
            jobContainerTeplate['env'][1]['value'] = apihost

        argsK8s = []
        for a in list(w['parameters'].keys()):
            arg = a + '=' + str(w['parameters'][a])
            argsK8s.append(arg)
        jobTeplate['spec']['template']['spec']['containers'][0]['args'] = argsK8s
        jobFile =  jobFile + '---\n' + yaml.dump(jobTeplate, default_flow_style=False)
    print(jobFile)


