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
import nuvolaris.config as cfg
import nuvolaris.couchdb_util as cu
import logging, json

from authorize import Authorize

USER_META_DBN = "users_metadata"

def fetch_user_data(db, login: str):
    logging.info(f"searching for user {login} data")
    try:
        selector = {"selector":{"login": {"$eq": login }}}
        response = db.find_doc(USER_META_DBN, json.dumps(selector))

        if(response['docs']):
                docs = list(response['docs'])
                if(len(docs) > 0):
                    return docs[0]
        
        logging.warn(f"Nuvolaris metadata for user {login} not found!")
        return None
    except Exception as e:
        logging.error(f"failed to query Nuvolaris metadata for user {login}. Reason: {e}")
        return None

def build_error(message: str):
    return {
        "statusCode": 400,
        "body": message
    }

def build_response(user_data):
    body = {}
    envs = list(user_data['env'])

    for env in envs:
        body[env['key']]=env['value']

    return {
        "statusCode": 200,
        "body": body
    }

def main(args):
    """
    Action implementing a generic command wrapper for the nuv devel plugin. The action must be called with a POST request receiving a JSON
    payload similar to this one
    {
        "provider":"redis",
        "type":"execute",
        "command":"<something to execute>",
        "args":[
            "arg0",
            "arg1"
        ]
    }

    the invoker must provide a x-impersonate-auth header which contains the BASIC authentication of the nuvolaris user to be used to submit the command to
    the provider.
    Every specific provider will support specific request type and command.
    """
    headers = args['__ow_headers']
    if('x-impersonate-auth' not in headers):
        return build_error("invalid request, missing mandatory header: x-impersonate-auth")

    if(len(args['__ow_body']) == 0):
        return build_error("invalid request, no command payload received")
    
    try:
        user_data = Authorize().login(headers['x-impersonate-auth'])

    except Exception as e:        
        return build_error(f"failed to execute nuv devel command. Reason: {e}")