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
import nuvolaris.util as util
from nuvolaris.user_config import UserConfig

class UserMetadata:
    _data = {}

    def __init__(self, ucfg: UserConfig):
        self._data = {
            "login":ucfg.get('namespace'),
            "password":ucfg.get('password'),
            "email":ucfg.get('email'),
            "metadata":[],
            "quota":[]
        }

        if ucfg.exists("object-storage.quota"):
            self.add_quota("OBJECT_STORAGE",ucfg.get("object-storage.quota"))

        if ucfg.exists("mongodb.quota"):
            self.add_quota("MONGODB",ucfg.get("mongodb.quota"))

        if ucfg.exists("redis.quota"):
            self.add_quota("REDIS",ucfg.get("redis.quota"))

        if ucfg.exists("postgres.quota"):
            self.add_quota("POSTGRES",ucfg.get("postgres.quota"))             

    def dump(self):
        logging.debug(json.dumps(self._data))

    def add_metadata(self, key: str, value: str):
        """
        append an entry to the metadata with this structure {"key":key, "value":value}
        """
        logging.debug(f"adding ({key}={value})")
        self._data['metadata'].append({"key":key, "value":value})

    def add_quota(self, key: str, value: str):
        """
        append an entry to the quota with this structure {"key":key, "value":value}
        """
        logging.debug(f"adding ({key}={value})")
        self._data['quota'].append({"key":key, "value":value})        

    def get_metadata(self):
        return self._data
    
    def add_safely_from_cm(self,metadata_key,json_path):
            try: 
                value = util.get_value_from_config_map("nuvolaris", json_path)
                if value:
                    self.add_metadata(metadata_key, value)
            except Exception as e:
                logging.warn(e)