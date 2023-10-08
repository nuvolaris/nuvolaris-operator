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
from base64 import b64decode, b64encode
from urllib.parse import quote, unquote

import nuvolaris.config as cfg
import nuvolaris.couchdb_util as cu
import json
import util as ut

USER_META_DBN = "users_metadata"

class DecodeError(Exception):
    pass

class EncodeError(Exception):
    pass

class AuthorizationError(Exception):
    pass

class Authorize():

    def __init__(self, cdb_host, cdb_user, cdb_pwd):
        cfg.clean()
        cfg.put("couchdb.host", cdb_host)
        cfg.put("couchdb.admin.user", cdb_user)
        cfg.put("couchdb.admin.password", cdb_pwd)
        self._db = cu.CouchDB()

    def encode(self,username, password):
        """Returns an HTTP basic authentication encrypted string given a valid
        username and password.
        """
        if ':' in username:
            raise EncodeError

        username_password = f'{quote(username)}:{quote(password)}'
        return f'Basic {b64encode(username_password.encode()).decode()}'


    def decode(sels, encoded_str):
        """Decode an encrypted HTTP basic authentication string. Returns a tuple of
        the form (username, password), and raises a DecodeError exception if
        nothing could be decoded.
        """
        split = encoded_str.strip().split(' ')

        # If split is only one element, try to decode the username and password
        # directly.
        if len(split) == 1:
            try:
                username, password = b64decode(split[0]).decode().split(':', 1)
            except:
                raise DecodeError

        # If there are only two elements, check the first and ensure it says
        # 'basic' so that we know we're about to decode the right thing. If not,
        # bail out.
        elif len(split) == 2:
            if split[0].strip().lower() == 'basic':
                try:
                    username, password = b64decode(split[1]).decode().split(':', 1)
                except:
                    raise DecodeError
            else:
                raise DecodeError

        # If there are more than 2 elements, something crazy must be happening.
        # Bail.
        else:
            raise DecodeError

        return unquote(username), unquote(password) 

    def fetch_user_data(self, username: str):
        """
        Query the internal mongodb searching for the given username
        """
        print(f"searching for user {username} data")
        try:
            selector = {"selector":{"login": {"$eq": username }}}
            response = self._db.find_doc(USER_META_DBN, json.dumps(selector))

            if(response['docs']):
                    docs = list(response['docs'])
                    if(len(docs) > 0):
                        print(f"Nuvolaris metadata for user {username} found. Returning Result.")
                        return docs[0]
            
            print(f"Nuvolaris metadata for user {username} not found!")
            return None
        except Exception as e:
            print(f"failed to query Nuvolaris metadata for user {username}. Reason: {e}")
            return None

    def login(self, authorization: str):
        """
        Attempt to login the user identified by the given Basic authorization token
        """
        username, password = self.decode(authorization)
        user_data = self.fetch_user_data(username)

        if user_data and password == ut.get_env_value(user_data,'AUTH'):
            return user_data
        
        raise AuthorizationError