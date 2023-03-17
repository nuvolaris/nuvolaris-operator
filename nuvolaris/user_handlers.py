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
# Provides extra kopf handlers to manage nuvolaris users
import kopf
import logging
import json, flatdict, os, os.path
import nuvolaris.config as cfg
import nuvolaris.couchdb as cdb
import nuvolaris.user_config as user_config

def get_ucfg(spec):
    ucfg = user_config.UserConfig(spec)
    ucfg.dump_config()
    return ucfg

@kopf.on.create('nuvolaris.org', 'v1', 'whisksusers')
def whisk_user_create(spec, name, **kwargs):
    logging.info(f"*** whisk_user_create {name}")
    state = {
    }

    ucfg = get_ucfg(spec)

    if(ucfg.get("namespace") and ucfg.get("password")):
        res = cdb.create_ow_user(ucfg.get("namespace"),ucfg.get("password"))
        logging.info(f"OpenWhisk subject {ucfg.get('namespace')} added = {res}")
        state['couchdb']= res

    return state

@kopf.on.delete('nuvolaris.org', 'v1', 'whisksusers')
def whisk_user_delete(spec, name, **kwargs):
    logging.info(f"*** whisk_user_delete {name}")

    ucfg = get_ucfg(spec)

    if(ucfg.get("namespace")):
        res = cdb.delete_ow_user(ucfg.get("namespace"))
        logging.info(f"OpenWhisk subject {ucfg.get('namespace')} removed = {res}")

@kopf.on.update('nuvolaris.org', 'v1', 'whisksusers')
def whisk_user_update(spec, status, namespace, diff, name, **kwargs):
    logging.info(f"*** detected an update of wsku/{name} under namespace {namespace}")