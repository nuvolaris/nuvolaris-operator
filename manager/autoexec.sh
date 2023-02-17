#!/bin/bash
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
echo AUTO DEPLOYING OPERATOR: "$OPERATOR_IMAGE:$OPERATOR_TAG"

cat << __EOF__> deploy/nuvolaris-operator/kustomization.yaml
      apiVersion: kustomize.config.k8s.io/v1beta1
      kind: Kustomization
      images:
      - name: ghcr.io/nuvolaris/nuvolaris-operator:latest
        newName: ${OPERATOR_IMAGE}
        newTag: ${OPERATOR_TAG}
      resources:
      - operator-pod.yaml
__EOF__

kubectl -n nuvolaris apply -k deploy/nuvolaris-operator
kubectl -n nuvolaris apply -f deploy/instance
touch /tmp/started
touch /tmp/healthy

echo 'starting operator liveness probe loop....'

while true
do PHASE=$(kubectl -n nuvolaris get pod/nuvolaris-operator -o jsonpath='{.status.phase}')
     if [ "$PHASE" == "Running" ];
     then 
      echo $PHASE > /tmp/healthy
     else 
      echo 'None' > /tmp/healthy
      echo 'operator not available'
     fi     
     sleep 5
done

exit 0




