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
import flatdict, json, os
import logging

class UserConfig:
    _config = {}

    def __init__(self, spec):
        self.configure(spec)
        pass

    # define a configuration 
    # the configuration is a map, followed by a list of labels 
    # the map can be a serialized json and will be flattened to a map of values.
    # you can have only a configuration active at a time
    # if you want to set a new configuration you have to clean it
    def configure(self,spec: dict):
        self._config = dict(flatdict.FlatDict(spec, delimiter="."))
        return True

    def clean(self):    
        self._config = {}

    def exists(self,key):
        return key in self._config

    def get(self,key, envvar=None, defval=None):
        val = self._config.get(key)

        if envvar and envvar in os.environ:
            val = os.environ[envvar]
        
        if val: 
            return val
        
        return defval

    def put(self,key, value):
        self._config[key] = value
        return True

    def delete(self, key):
        if key in self._config:
            del self._config[key]
            return True

    def getall(self,prefix=""):
        res = {}
        for key in self._config.keys():
            if key.startswith(prefix):
                res[key] = self._config[key]
        return res

    def keys(self, prefix=""):
        res = []
        if self._config:
            for key in self._config.keys():
                if key.startswith(prefix):
                    res.append(key)
        return res

    def dump_config(self):
        for k in self.getall():
            logging.debug(f"{k} = {self._config.get(k)}")

