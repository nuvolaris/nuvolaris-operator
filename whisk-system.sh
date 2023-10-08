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
mkdir -p ${HOME}/actions/upload/common
cp ${HOME}/actions/common/minio_util.py ${HOME}/actions/upload/common
rm  -f ${HOME}/deploy/whisk-system/upload.zip
zip -r ${HOME}/deploy/whisk-system/upload.zip *

mkdir -p ${HOME}/actions/redis/nuvolaris
mkdir -p ${HOME}/actions/redis/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/redis/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/redis/common
cd ${HOME}/actions/redis
rm  -f ${HOME}/deploy/whisk-system/redis.zip
zip -r ${HOME}/deploy/whisk-system/redis.zip *

mkdir -p ${HOME}/actions/psql/nuvolaris
mkdir -p ${HOME}/actions/psql/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/psql/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/psql/common
cd ${HOME}/actions/psql
rm  -f ${HOME}/deploy/whisk-system/psql.zip
zip -r ${HOME}/deploy/whisk-system/psql.zip *

mkdir -p ${HOME}/actions/minio/nuvolaris
mkdir -p ${HOME}/actions/minio/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/minio/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/minio/common
cd ${HOME}/actions/minio
rm  -f ${HOME}/deploy/whisk-system/minio.zip
zip -r ${HOME}/deploy/whisk-system/minio.zip *

mkdir -p ${HOME}/actions/devel_upload/nuvolaris
mkdir -p ${HOME}/actions/devel_upload/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/devel_upload/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/devel_upload/common
cd ${HOME}/actions/devel_upload
rm  -f ${HOME}/deploy/whisk-system/devel_upload.zip
zip -r ${HOME}/deploy/whisk-system/devel_upload.zip *
