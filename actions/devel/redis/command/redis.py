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
import redis

from common.command_data import CommandData

class Redis():
    """
    Implementation of a Redis Command executor. It will require
    a user_data dictionary linked to a specific user.
    """

    def __init__(self, user_data):
        self._user_data = user_data        
        self._redis_prefix = ut.get_env_value(user_data,"REDIS_PREFIX")
        self._redis_url = ut.get_env_value(user_data,"REDIS_URL")
        self.validate()

    def validate(self):
        """
        Validate that the provided user_data contains the appropriate
        metadata for being able to submit a redis command.
        """
        if not self._redis_prefix or not self._redis_url: 
            raise Exception("user does not have valid REDIS environment set")
        
    def execute(self, input:CommandData):
        print(f"**** Redis command to execute {input.command()}")        
        try:
            r = redis.from_url(self._redis_url)
            result = r.execute_command(input.command())
            input.result(str(result.decode('utf-8')))
            input.status(200)
        except Exception as e:
            input.result(f"could not execute redis command {e}")
            input.status(400)

        return input