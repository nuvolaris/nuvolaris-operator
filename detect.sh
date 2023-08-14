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
if test -e detect.force
then cat detect.force ; exit 0
fi
if ! test -e .env
then echo "kind" ; exit 0
else export $(grep -v '^#' .env | xargs)
fi
if test -n "$MY_DETECT"
then echo "$MY_DETECT" ; exit 0
fi
LABELS="$(kubectl get nodes -ojsonpath='{.items[].metadata.labels}' 2>/dev/null)"
#echo $LABELS | jq .
if echo "$LABELS" | jq . | grep eksctl.io >/dev/null
then echo "eks"
elif echo "$LABELS" | jq . | grep microk8s.io >/dev/null
then echo "microk8s"
elif echo "$LABELS" | jq . | grep lke.linode.com >/dev/null
then echo "lks"
elif echo "$LABELS" | jq . | grep cloud.google.com/gke >/dev/null
then echo "gke"
elif echo "$LABELS" | jq . | grep kubernetes.azure.com >/dev/null
then echo "aks"
elif echo "$LABELS" | jq . | grep openshift.io >/dev/null
then echo "openshift"
elif echo "$LABELS" | jq . | grep 'instance-type.*k3s' >/dev/null
then echo "k3s"
elif echo "$LABELS" | jq . | awk '/nuvolaris.io\/kube/ {print $2}' | grep kind >/dev/null
then echo "kind"
else echo "generic"
fi
