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

import common.util as ut
import json


from pymongo import MongoClient
from common.command_data import CommandData

class FerretDB():
    """
    Implementation of a FerretDB/Mongodb Command executor. It will require
    a user_data dictionary linked to a specific user.
    """

    def __init__(self, user_data):
        self._user_data = user_data        
        self._mdb_url = ut.get_env_value(user_data,"MONGODB_URL")
        self._db = user_data['login']
        self.validate()

    def validate(self):
        """
        Validate that the provided user_data contains the appropriate
        metadata for being able to submit a redis command.
        """
        if not self._mdb_url or not self._db: 
            raise Exception("user does not have valid FERRETDB/MONGODB environment set")

    def _get_db(self):
        """
        Get a reference to the connected user database
        """
        client = MongoClient(self._mdb_url)
        return client[self._db]


    def _send_command(self,input:CommandData):
        print(f"inside ferretdb _send_command {json.dumps(input.get_raw_data())}")        
        db = self._get_db()
        response = db.command(input.get_raw_data())

        if response:                
            input.result(str(response))
            input.status(200)               
        else:    
            input.result(f"ferretdb/mongodb operation failed")
            input.status(400)          
        
    def execute(self, input:CommandData):      
        try:           
            input.status(400)            
            self._send_command(input)
        except Exception as e:
            print(e)
            input.result(f"could not execute ferretbd command {e}")
            input.status(400)

        return input