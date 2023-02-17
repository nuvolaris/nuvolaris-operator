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
# Nuvolaris Operator Manager

This is an example of a manager for the Kubernetes Operator of the [bit.ly/nuvolaris](nuvolaris project).

## Notes

The purpose it is to provide an image that could be used to deploy a pod (or better a static pod) to deploy automatically the nuvolaris operator. 

This is the current status:

- Nuvolaris manger image is built by importing operator configuration files that are valid for any supported kubernetes engine. 
- The nuvolaris operator instance is created using a whisk.yaml file suitable for Kind deployment only
- The manager image has been tested by deploying a Pod running the nuvolaris manager image under the kube-system namespace with a service account having the same permssion set as the nuvolaris-operator

## How to build and test
Project subfolder contains a Taskfile.yaml, which is imported into the operatore main Task file under the prefix manager. To customize the image name it is possible to add *MY_MANAGER_IMAGE=* into the .env file used for the operator development.

Use:

- task manager:build-and-load to build and load the image onto the current kubernetes cluster
- task manager:test to deploy under the kube-system namespace a pod called pod/nuvolaris-operator-manager

### Note
Under the *kind* folder there is an experimental version of a kind nuvolaris cluster setup which deploys a pod/nuvolaris-operator-manager without creating a specific service account with RBAC permission, but:
- makes available the generated kube config as a configMap under the kube-system namespace
- deploys a pod/nuvolaris-operator-manager using the above generated configMap to overrides the default kubeconfig provided by Kubernetes to any running Pod.

