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
from nuvolaris.user_config import UserConfig

class UserMetadata:
    _data = {}

    def __init__(self, ucfg: UserConfig):
        self._data = {
            "login":ucfg.get('namespace'),
            "password":ucfg.get('password'),
            "email":ucfg.get('email'),
            "metadata":[]
    }

    def dump(self):
        logging.debug(json.dumps(self._data))

    def add_metadata(self, key: str, value: str):
        """
        append an entry to the metadata with this structure {"key":key, "value":value}
        """
        logging.debug(f"adding {key,value}={key},{value}")
        self._data['metadata'].append({"key":key, "value":value})

    def get_metadata(self):
        return self._data  
    

