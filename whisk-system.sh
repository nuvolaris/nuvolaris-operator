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
echo CONTROLLER: "$CONTROLLER_IMAGE:$CONTROLLER_TAG"
echo OPERATOR: "$OPERATOR_IMAGE:$OPERATOR_TAG"

echo preparing nuvolaris system actions....

mkdir -p ${HOME}/actions/login/nuvolaris
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/login/nuvolaris
cd ${HOME}/actions/login
rm  -f ${HOME}/deploy/whisk-system/login.zip
zip -r ${HOME}/deploy/whisk-system/login.zip *
cd ${HOME}/actions/upload
rm  -f ${HOME}/deploy/whisk-system/upload.zip
zip -r ${HOME}/deploy/whisk-system/upload.zip *
