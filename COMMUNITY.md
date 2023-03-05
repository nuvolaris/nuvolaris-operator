<!--
  ~ Licensed to the Apache Software Foundation (ASF) under one
  ~ or more contributor license agreements.  See the NOTICE file
  ~ distributed with this work for additional information
  ~ regarding copyright ownership.  The ASF licenses this file
  ~ to you under the Apache License, Version 2.0 (the
  ~ "License"); you may not use this file except in compliance
  ~ with the License.  You may obtain a copy of the License at
  ~
  ~   http://www.apache.org/licenses/LICENSE-2.0
  ~
  ~ Unless required by applicable law or agreed to in writing,
  ~ software distributed under the License is distributed on an
  ~ "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
  ~ KIND, either express or implied.  See the License for the
  ~ specific language governing permissions and limitations
  ~ under the License.
  ~
-->
# Nuvolaris Community Operator

This is the Community Kubernetes Operator of the [bit.ly/nuvolaris](nuvolaris project).

## Customization notes

Nuvolaris operators it is normally deploy using a `whisk.yaml` configuration file which is applied via the installer. Typically the customization file contains something like

```
apiVersion: nuvolaris.org/v1
kind: Whisk
metadata:
  name: controller
  namespace: nuvolaris
spec:
  nuvolaris:
      apihost: <ip address or hostname to be assigned to nuvolaris controller ingress>
  components:
    # start openwhisk controller
    openwhisk: true   
    # start couchdb
    couchdb: true
    # start mongodb
    mongodb: true
    # start redis
    redis: true  
    # start simple internal cron     
    cron: true 
    # tls enabled or not
    tls: false
    # minio enabled or not
    minio: true    
  openwhisk:
    namespaces:
      whisk-system: xxxx:yyyyyy
      nuvolaris: ccccc:zzzzz
  couchdb:
    host: couchdb
    port: 5984
    volume-size: 10
    admin:
      user: <couch_db_admin_user>
      password: <couch_db_admin_pwd>
    controller:
      user: <couch_db_controller_user>
      password: <couch_db_controller_user>
  mongodb:
    host: mongodb
    volume-size: 10
    admin: 
      user: <mongodb_db_admin_user>
      password: <mongodb_db_admin_pwd>
    nuvolaris:
      user: <mongodb_db_nuvolaris_user>
      password: <mongodb_db_nuvolaris_pwd>    
    useOperator: False
  scheduler:
    schedule: "* * * * *"
  tls:
    acme-registered-email: xxxxx@youremailserver.com
    acme-server-url: https://acme-staging-v02.api.letsencrypt.org/directory
  minio:
    volume-size: 2
    nuvolaris:
      root-user: <minio_admin_user>
      root-password: <minio_admin_pwd>
  configs:    
    limits:
      actions:
        sequence-maxLength: 50
        invokes-perMinute: 999
        invokes-concurrent: 250
      triggers: 
        fires-perMinute: 999
      time:
        limit-min: "100ms"  
        limit-std: "1min"
        limit-max: "5min"
      memory:
        limit-min: "128m"
        limit-std: "256m"
        limit-max: "512m" 
    controller:
      javaOpts: "-Xmx2048M"        
```

## Default configs values
If the provided `whisk.yaml` does not specify any dynamic configuration parameteres under `configs` item, the Community operators defaults to these values:

- `configs.limit.actions.sequence-maxLength=50`
- `configs.limit.actions.invokes-perMinute=60`
- `configs.limit.actions.invokes-concurrent=30`
- `configs.limit.actions.triggers.fires-perMinute=60`
- `configs.limits.time.limit-min=100ms`
- `configs.limits.time.limit-std=1min`
- `configs.limits.time.limit-max=5min`
- `configs.limits.memory.limit-min=128m`
- `configs.limits.memory.limit-std=256m`
- `configs.limits.memory.limit-max=512m`
- `configs.controller.javaOpts=-Xmx2048M`

## Openwhisk Controller hot deployment

The community operator supports hot deployment for the Openwhisk Controller, i.e it is possible to modify some specific part of the configuration inside the `whisk.yaml` file and apply it again. The operator
will automatically stop and redeploy the controller to take into account the new settings.

```
  configs:    
    limits:
      actions:
        sequence-maxLength: 50
        invokes-perMinute: 999
        invokes-concurrent: 250
      triggers: 
        fires-perMinute: 999
      time:
        limit-min: "100ms"  
        limit-std: "1min"
        limit-max: "5min"
      memory:
        limit-min: "128m"
        limit-std: "256m"
        limit-max: "512m" 
    controller:
      javaOpts: "-Xmx2048M"
```

As an example, using the above configuration and taking into account the standard 256m memory size limit per action, gives the possibility to execute around 8 action concurrently [`As a general rule consider it as the result of controller.javaOpts/256m`]. To increase the number of estimated action that can be executed modify for example `controller.javaOpts:"-Xmx4096M"` and redeploy the modified `whisk.yaml`.

To apply the new customization execute

```
kubectl -n nuvolaris apply -f whisk.yaml
```