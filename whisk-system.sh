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
mkdir -p ${HOME}/deploy/whisk-system
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/login/nuvolaris
cd ${HOME}/actions/login
rm  -f ${HOME}/deploy/whisk-system/login.zip
zip -r ${HOME}/deploy/whisk-system/login.zip *

cd ${HOME}/actions/content
mkdir -p ${HOME}/actions/content/common
cp ${HOME}/actions/common/minio_util.py ${HOME}/actions/content/common
rm  -f ${HOME}/deploy/whisk-system/content.zip
zip -r ${HOME}/deploy/whisk-system/content.zip *

mkdir -p ${HOME}/actions/devel/redis/nuvolaris
mkdir -p ${HOME}/actions/devel/redis/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/devel/redis/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/devel/redis/common
cd ${HOME}/actions/devel/redis
rm  -f ${HOME}/deploy/whisk-system/redis.zip
zip -r ${HOME}/deploy/whisk-system/redis.zip *

mkdir -p ${HOME}/actions/devel/psql/nuvolaris
mkdir -p ${HOME}/actions/devel/psql/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/devel/psql/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/devel/psql/common
cd ${HOME}/actions/devel/psql
rm  -f ${HOME}/deploy/whisk-system/psql.zip
zip -r ${HOME}/deploy/whisk-system/psql.zip *

mkdir -p ${HOME}/actions/devel/minio/nuvolaris
mkdir -p ${HOME}/actions/devel/minio/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/devel/minio/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/devel/minio/common
cd ${HOME}/actions/devel/minio
rm  -f ${HOME}/deploy/whisk-system/minio.zip
zip -r ${HOME}/deploy/whisk-system/minio.zip *

mkdir -p ${HOME}/actions/devel/ferretdb/nuvolaris
mkdir -p ${HOME}/actions/devel/ferretdb/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/devel/ferretdb/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/devel/ferretdb/common
cd ${HOME}/actions/devel/ferretdb
rm  -f ${HOME}/deploy/whisk-system/ferretdb.zip
zip -r ${HOME}/deploy/whisk-system/ferretdb.zip *

mkdir -p ${HOME}/actions/devel/download/nuvolaris
mkdir -p ${HOME}/actions/devel/download/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/devel/download/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/devel/download/common
cd ${HOME}/actions/devel/download
rm  -f ${HOME}/deploy/whisk-system/devel_download.zip
zip -r ${HOME}/deploy/whisk-system/devel_download.zip *

mkdir -p ${HOME}/actions/devel/upload/nuvolaris
mkdir -p ${HOME}/actions/devel/upload/common
cp ${HOME}/nuvolaris/config.py ${HOME}/nuvolaris/couchdb_util.py ${HOME}/actions/devel/upload/nuvolaris
cp ${HOME}/actions/common/*.py ${HOME}/actions/devel/upload/common
cd ${HOME}/actions/devel/upload
rm  -f ${HOME}/deploy/whisk-system/devel_upload.zip
zip -r ${HOME}/deploy/whisk-system/devel_upload.zip *
