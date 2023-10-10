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
import json

from common.authorize import Authorize
from common.command_data import CommandData
from command.ferretbd import FerretDB
from base64 import b64decode

class ApiError(Exception):
    pass

def build_error(message: str):
    return {
        "statusCode": 400,
        "body": message
    }

def build_response(data:CommandData):
    meta_data = data.get_metadata()
    return {
        "statusCode": meta_data['status'],
        "body": meta_data['result']
    }

def parse_body(args):
    try:
        return b64decode(args['__ow_body']).decode().strip()        
    except Exception as e:
        print(e)
        raise ApiError("could not parse __ow_body as base64")

def main(args):
    """
    Action implementing a generic command wrapper for the nuv devel mdb/ferretdb plugin. The action must be called with a POST request receiving a JSON
    payload similar to this one
    {
        "command":"SET nuvolaris:key1 donald_duck"
    }

    the invoker must provide a x-impersonate-auth header containing the Openwhisk BASIC authentication of the wsku/user the action should impersonate 
    when submitting the command. Every specific provider will support specific request type and command.
    WARNING: the body will be received as base64 encoded string as this action will be deployed with --web raw enabled flag
    """
    print(args)
    headers = args['__ow_headers']
    if('x-impersonate-auth' not in headers):
        return build_error("invalid request, missing mandatory header: x-impersonate-auth")

    if(len(args['__ow_body']) == 0):
        return build_error("invalid request, no command payload received")
    
    try:        
        user_data = Authorize(args['couchdb_host'],args['couchdb_user'],args['couchdb_password']).login(headers['x-impersonate-auth'])               
        cmd = CommandData(json.loads(parse_body(args)))           
        return build_response(FerretDB(user_data).execute(cmd))
    except Exception as e:        
        return build_error(f"failed to execute nuv devel ferretdb. Reason: {str(e)}")