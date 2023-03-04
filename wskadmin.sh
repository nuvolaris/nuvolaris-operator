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
cd "$(dirname $0)"
configure() { 
    if test -e whisk.properties
    then return
    fi
    if ! kubectl -n nuvolaris get wsk/controller 2>/dev/null >/dev/null
    then 
        echo "Nuvolaris not yet configured"
        exit 1
    fi
    DB_USER="$(kubectl -n nuvolaris get wsk/controller -ojsonpath='{.spec.couchdb.admin.user}')"
    DB_PASS="$(kubectl -n nuvolaris get wsk/controller -ojsonpath='{.spec.couchdb.admin.password}')"
    DB_HOST="$(kubectl -n nuvolaris get wsk/controller -ojsonpath='{.spec.couchdb.host}')"
    cat <<EOF >whisk.properties
whisk.logs.dir=/var/tmp/wsklogs
db.host=$DB_HOST
db.username=$DB_USER
db.password=$DB_PASS
db.provider=CouchDB
db.protocol=http
db.port=5984
db.prefix=nuvolaris_
db.whisk.auths=nuvolaris_subjects
db.whisk.actions=nuvolaris_whisks
db.whisk.activations=nuvolaris_activations
EOF
}

configure
poetry run python tools/cli/wsk/wskadmin.py "$@"
