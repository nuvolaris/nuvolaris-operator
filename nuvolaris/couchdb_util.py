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
import os, json, time, sys, logging
import requests as req
import nuvolaris.config as cfg

class CouchDB:
  def __init__(self):
    self.db_protocol   = "http"
    self.db_prefix     = "nuvolaris_"
    self.db_port       = cfg.get("couchdb.port", "COUCHDB_SERVICE_PORT", "5984")
    self.db_host       = cfg.get("couchdb.host", "COUCHDB_SERVICE_HOST", "couchdb")
    self.db_username   = cfg.get("couchdb.admin.user", "COUCHDB_ADMIN_USER", "whisk_admin")
    self.db_password   = cfg.get("couchdb.admin.password", "COUCHDB_ADMIN_PASSWORD", "some_passw0rd")
    self.db_auth = req.auth.HTTPBasicAuth(self.db_username,self.db_password)
    self.db_url = f"{self.db_protocol}://{self.db_host}:{self.db_port}"
    self.db_base = f"{self.db_url}/{self.db_prefix}"
    self.db_session = req.Session()
    self.db_session.auth = self.db_auth

  def wait_db_ready(self, max_seconds):
      logging.info("entering CouchDB.wait_db_ready()")
      start = time.time()
      delta = 0
      session = req.Session()
      while delta < max_seconds:
        try:
          r = session.get(f"{self.db_url}/_utils", timeout=5)
          logging.info(f"CouchDB.wait_db_ready() got response code = {r.status_code}")          
          if r.status_code == 200:
            return True
        except Exception as e:
          logging.info(f"waiting since: {delta} seconds")
        delta = int(time.time() - start)
        time.sleep(1)
      return False

  # check if database exists, return boolean
  def check_db(self, database):
    url = f"{self.db_base}{database}"
    r = self.db_session.head(url)
    return r.status_code == 200
  
  # delete database, return true if ok
  def delete_db(self, database):
    url = f"{self.db_base}{database}"
    r = self.db_session.delete(url)
    return r.status_code == 200

  # create db, return true if ok
  def create_db(self, database):
    url = f"{self.db_base}{database}"
    r = self.db_session.put(url) 
    return r.status_code == 201

  # database="subjects"
  def recreate_db(self, database, recreate=False):
    msg = "recreate_db:"
    exists = self.check_db(database)
    if recreate and exists:
      msg += " deleted"
      self.delete_db(database)
    if recreate or not exists:
      msg += " created"
      self.create_db(database)
    return msg

  def get_doc(self, database, id, user=None, password="", no_auth=False):
    url = f"{self.db_base}{database}/{id}"
    session = req.Session()
    if no_auth:
      db_auth=None
    elif user:
      db_auth=req.auth.HTTPBasicAuth(user, password)
    else:
      db_auth = self.db_auth
    session.auth =  db_auth 
    r = session.get(url) 
    if r.status_code == 200:
      return json.loads(r.text)
    return None

  def update_doc(self, database, doc):
    if '_id' in doc:
      url = f"{self.db_base}{database}/{doc['_id']}"
      cur = self.get_doc(database, doc['_id'])
      if cur and '_rev' in cur:
        doc['_rev'] = cur['_rev']
        r = self.db_session.put(url, json=doc)
      else:
        r = self.db_session.put(url,  json=doc)
      return r.status_code in [200,201]
    return False

  def delete_doc(self, database, id):
    cur = self.get_doc(database, id)
    if cur and '_rev' in cur:
        url = f"{self.db_base}{database}/{cur['_id']}?rev={cur['_rev']}"
        r = self.db_session.delete(url)
        return r.status_code == 200
    return False

  def configure_single_node(self):
    url = f"{self.db_url}/_cluster_setup"
    data = {"action": "enable_single_node", "singlenode": True, "bind_address": "0.0.0.0", "port": 5984}
    r = self.db_session.post(url, json=data) 
    return r.status_code == 201

  def configure_no_reduce_limit(self):
    url = f"{self.db_url}/_node/_local/_config/query_server_config/reduce_limit"
    data=b'"false"'
    r = self.db_session.put(url, data=data) 
    return r.status_code == 200

  def add_user(self, username: str, password: str):
    userpass = {"name": username, "password": password, "roles": [], "type": "user"}
    url = f"{self.db_url}/_users/org.couchdb.user:{username}"
    res = self.db_session.put(url, json=userpass)
    return res.status_code in [200, 201, 421]

  #def add_role(self, database: str, members: list[str] = [], admins: list[str] =[]):  
  def add_role(self, database: str, members = [], admins =[]):  
    roles =  {"admins": { "names": admins, "roles": [] }, "members": { "names": members, "roles": [] } }
    url = f"{self.db_base}{database}/_security"
    res = self.db_session.put(url, json=roles)
    return res.status_code in [200, 201, 421]

#
# Submit a POST request to the _find endpoint using the specified selector
#
  def find_doc(self, database, selector, user=None, password="", no_auth=False):
    url = f"{self.db_base}{database}/_find"
    headers = {'Content-Type': 'application/json'}
    session = req.Session()

    if no_auth:
      db_auth=None
    elif user:
      db_auth=req.auth.HTTPBasicAuth(user, password)
    else:
      db_auth = self.db_auth

    session.auth=db_auth  
    r = session.post(url, headers=headers, data=selector)
    if r.status_code == 200:
      return json.loads(r.text)
    
    logging.warn(f"query to {url} failed with {r.status_code}. Body {r.text}")
    return None    