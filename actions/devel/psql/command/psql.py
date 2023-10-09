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

import psycopg
import common.util as ut

from common.command_data import CommandData
from psycopg.rows import dict_row

class Psql():
    """
    Implementation of a Postgres Command executor. It will require
    a user_data dictionary linked to a specific user.
    """

    def __init__(self, user_data):
        self._user_data = user_data        
        self._postgres_url= ut.get_env_value(user_data,"POSTGRES_URL")        
        self.validate()

    def validate(self):
        """
        Validate that the provided user_data contains the appropriate
        metadata for being able to submit a postgres command.
        """
        if not self._postgres_url: 
            raise Exception("user does not have valid POSTGRES environment set")


    def _query(self, input:CommandData):
        """
        Queries for matching query records and returns datas in a key, value format.
        """
        query = input.command()
        with psycopg.connect(self._postgres_url) as conn:
            # Open a cursor to perform database operations
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                result = cur.fetchall()                
                input.result(str(result))
                input.status(200)
                return input

    def _script(self, input:CommandData):
        script = input.command()
        with psycopg.connect(self._postgres_url) as conn:
            # Open a cursor to perform database operations
            with conn.cursor() as cur:
                cur.execute(script)
                conn.commit()
                input.result(cur.statusmessage)
                input.status(200)
                return input                
            
    def _is_a_query(self, input:CommandData):        
        return 'select' in input.command().lower()

    def execute(self, input:CommandData):
        print(f"**** Psql command to execute {input.command()}")        
        try:
            if self._is_a_query(input):
                return self._query(input)
            else:
                return self._script(input)
        except Exception as e:
            input.result(f"could not execute psql command {e}")
            input.status(400)

        return input