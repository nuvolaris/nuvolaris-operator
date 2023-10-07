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
import logging, json
import nuvolaris.config as cfg
import nuvolaris.couchdb as cdb
import nuvolaris.couchdb_util as couchdb_util
import nuvolaris.user_config as user_config
import nuvolaris.util as util
import nuvolaris.mongodb as mdb
from nuvolaris.user_metadata import UserMetadata
from nuvolaris.nuvolaris_metadata import NuvolarisMetadata

USER_META_DBN = "users_metadata"

def _add_metadata(db, metadata):
    """
    Add a new Openwhisk User metadata entry     
    """
    res = util.check(db.wait_db_ready(60), "wait_db_ready", True)
    return util.check(cdb.update_templated_doc(db, USER_META_DBN, "user_metadata.json", metadata), f"add_metadata {metadata['login']}", res)
    
def save_user_metadata(user_metadata:UserMetadata):
    """
    Add a generic user metadata into the internal CouchDB 
    """
    metadata = user_metadata.get_metadata()
    logging.info(f"Storing Nuvolaris metadata for {metadata['login']}")

    try:
        db = couchdb_util.CouchDB()
        return _add_metadata(db, metadata)
    except Exception as e:
        logging.error(f"failed to store Nuvolaris metadata for {metadata['login']}. Cause: {e}")
        return None

def save_nuvolaris_metadata(nuvolaris_metadata:NuvolarisMetadata):
    """
    Add nuvolaris user metadata into the internal CouchDB 
    """
    metadata = nuvolaris_metadata.get_metadata()
    logging.info(f"Storing Nuvolaris metadata for {metadata['login']}")

    try:
        db = couchdb_util.CouchDB()
        return _add_metadata(db, metadata)
    except Exception as e:
        logging.error(f"failed to store Nuvolaris metadata for {metadata['login']}. Cause: {e}")
        return None        

def delete_user_metadata(login):
    logging.info(f"removing Nuvolaris metadata for user {login}")

    try:
        db = couchdb_util.CouchDB()
        selector = {"selector":{"login": {"$eq": login }}}
        response = db.find_doc(USER_META_DBN, json.dumps(selector))

        if(response['docs']):
                docs = list(response['docs'])
                if(len(docs) > 0):
                    doc = docs[0]
                    logging.info(f"removing user metadata documents {doc['_id']}")
                    return db.delete_doc(USER_META_DBN,doc['_id'])
        
        logging.warn(f"Nuvolaris metadata for user {login} not found!")
        return None
    except Exception as e:
        logging.error(f"failed to remove Nuvolaris metadata for user {login}. Reason: {e}")
        return None