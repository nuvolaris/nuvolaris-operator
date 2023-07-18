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
import json, os, os.path
import nuvolaris.config as cfg
import nuvolaris.couchdb as cdb
import nuvolaris.minio as minio
import nuvolaris.kube as kube
import nuvolaris.ferretdb as mdb
import nuvolaris.minio_static as static
import nuvolaris.redis as redis
import nuvolaris.userdb_util as userdb
import nuvolaris.postgres_operator as postgres

from nuvolaris.user_config import UserConfig
from nuvolaris.user_metadata import UserMetadata

def get_ucfg(spec):
    ucfg = UserConfig(spec)
    ucfg.dump_config()
    return ucfg

@kopf.on.create('nuvolaris.org', 'v1', 'whisksusers')
def whisk_user_create(spec, name, **kwargs):
    logging.info(f"*** whisk_user_create {name}")
    state = {
    }

    ucfg = get_ucfg(spec)
    user_metadata = UserMetadata(ucfg)
    owner = kube.get(f"wsku/{name}")
    
    if(ucfg.get("namespace") and ucfg.get("auth")):
        res = cdb.create_ow_user(ucfg,user_metadata)
        logging.info(f"OpenWhisk subject {ucfg.get('namespace')} added = {res}")
        state['couchdb']= res

    if(cfg.get('components.minio') and (ucfg.get('object-storage.data.enabled') or ucfg.get('object-storage.route.enabled'))):        
        minio.create_ow_storage(state, ucfg, user_metadata, owner)

    if(cfg.get('components.minio') and ucfg.get('object-storage.route.enabled') and cfg.get('components.static')):
        res = static.create_ow_static_endpoint(ucfg,user_metadata, owner)
        logging.info(f"OpenWhisk static endpoint for {ucfg.get('namespace')} added = {res}")
        state['static']= res

    if(cfg.get('components.mongodb') and ucfg.get('mongodb.enabled')):
        res = mdb.create_db_user(ucfg,user_metadata)
        logging.info(f"Mongodb setup for {ucfg.get('namespace')} added = {res}")
        state['mongodb']= res

    if(cfg.get('components.redis') and ucfg.get('redis.enabled')):
        res = redis.create_db_user(ucfg, user_metadata)
        logging.info(f"Redis setup for {ucfg.get('namespace')} added = {res}")
        state['redis']= res

    if(cfg.get('components.postgres') and ucfg.get('postgres.enabled')):
        res = postgres.create_db_user(ucfg, user_metadata)
        logging.info(f"Postgres setup for {ucfg.get('namespace')} added = {res}")
        state['postgres']= res        

    # finally persists user metadata into the internal couchdb database
    user_metadata.dump()
    res = userdb.save_user_metadata(user_metadata)
    state['user_metadata']= res          

    return state

@kopf.on.delete('nuvolaris.org', 'v1', 'whisksusers')
def whisk_user_delete(spec, name, **kwargs):
    logging.info(f"*** whisk_user_delete {name}")

    ucfg = get_ucfg(spec)

    if(ucfg.get("namespace")):
        res = cdb.delete_ow_user(ucfg.get("namespace"))
        logging.info(f"OpenWhisk subject {ucfg.get('namespace')} removed = {res}")

    if(cfg.get('components.minio') and (ucfg.get('object-storage.data.enabled') or ucfg.get('object-storage.route.enabled'))):        
        res = minio.delete_ow_storage(ucfg)
        logging.info(f"OpenWhisk namespace {ucfg.get('namespace')} storage removed = {res}")

    if(cfg.get('components.minio') and ucfg.get('object-storage.route.enabled') and cfg.get('components.static')):
        res = static.delete_ow_static_endpoint(ucfg)
        logging.info(f"OpenWhisk static endpoint for {ucfg.get('namespace')} removed = {res}")

    if(cfg.get('components.mongodb') and ucfg.get('mongodb.enabled')):
        res = mdb.delete_db_user(ucfg.get('namespace'),ucfg.get('mongodb.database'))
        logging.info(f"Mongodb setup for {ucfg.get('namespace')} removed = {res}")

    if(cfg.get('components.redis') and ucfg.get('redis.enabled')):
        res = redis.delete_db_user(ucfg.get('namespace'))
        logging.info(f"Redis setup for {ucfg.get('namespace')} removed = {res}")

    if(cfg.get('components.postgres') and ucfg.get('postgres.enabled')):
        res = postgres.delete_db_user(ucfg.get('namespace'),ucfg.get('postgres.database'))
        logging.info(f"Postgres setup for {ucfg.get('namespace')} removed = {res}")        

    res = userdb.delete_user_metadata(ucfg.get('namespace'))


@kopf.on.update('nuvolaris.org', 'v1', 'whisksusers')
def whisk_user_update(spec, status, namespace, diff, name, **kwargs):
    logging.info(f"*** detected an update of wsku/{name} under namespace {namespace}")

@kopf.on.resume('nuvolaris.org', 'v1', 'whisksusers')
def whisk_user_resume(spec, name, namespace, **kwargs):
    logging.info(f"*** detected an update of wsku/{name} under namespace {namespace}")
    ucfg = get_ucfg(spec)
    user_metadata = UserMetadata(ucfg)

    state = {}
    
    if(cfg.get('components.redis') and ucfg.get('redis.enabled')):
        res = redis.create_db_user(ucfg,user_metadata)
        logging.info(f"Redis setup for {ucfg.get('namespace')} resumed = {res}")
        state['redis']= res

    if(cfg.get('components.minio') and ucfg.get('object-storage.route.enabled') and cfg.get('components.static')):
        state['static']= True

    if(cfg.get('components.mongodb') and ucfg.get('mongodb.enabled')):
        state['mongodb']= True          