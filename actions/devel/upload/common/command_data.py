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
import logging

class CommandData:
    _data = {}
    _raw_data = {}

    def __init__(self, cmd):
        self._data = cmd
        self._raw_data = cmd.copy()

    def dump(self):
        logging.debug(json.dumps(self._data))

    def status(self, status):
        self._data['status']=status

    def result(self, result):
        self._data['result']=result

    def get_metadata(self):
        return self._data
    
    def get_raw_data(self):
        return self._raw_data

    def command(self):
        return self._data['command'] 

    def args(self):
        return self._data['args']
    

