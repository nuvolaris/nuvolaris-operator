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
import nuvolaris.config as cfg
import nuvolaris.util as util

class NuvolarisMetadata:
    _data = {}

    def __init__(self):
        self._data = {
            "login":"nuvolaris",
            "password":cfg.get('nuvolaris.password') or "nuvpassw0rd",
            "email":cfg.get('nuvolaris.email') or "nuvolaris@nuvolaris.io",
            "metadata":[]            
        }

        self._configure_from_cm()

    
    def _store_safely_from_cm(self,metadata_key,json_path):
        try: 
            value = util.get_value_from_config_map("nuvolaris", json_path)
            if value:
                self.add_metadata(metadata_key, value)
        except Exception as e:
            logging.warn(e)        
    
    def _configure_from_cm(self):
        """
        Populates the internal metadata starting from the cm/config map
        """        
        self.add_metadata("AUTH", cfg.get('openwhisk.namespaces.nuvolaris'))
        self._store_safely_from_cm("MINIO_ACCESS_KEY", '{.metadata.annotations.minio_access_key}')
        self._store_safely_from_cm("MINIO_DATA_BUCKET", '{.metadata.annotations.minio_bucket_data}')
        self._store_safely_from_cm("MINIO_HOST", '{.metadata.annotations.minio_host}') 
        self._store_safely_from_cm("MINIO_PORT", '{.metadata.annotations.minio_port}')  
        self._store_safely_from_cm("MINIO_SECRET_KEY", '{.metadata.annotations.minio_secret_key}')    
        self._store_safely_from_cm("MINIO_STATIC_BUCKET", '{.metadata.annotations.minio_bucket_static}')
        self._store_safely_from_cm("MONGODB_URL", '{.metadata.annotations.mongodb_url}')
        self._store_safely_from_cm("POSTGRES_DATABASE", '{.metadata.annotations.postgres_database}') 
        self._store_safely_from_cm("POSTGRES_HOST", '{.metadata.annotations.postgres_host}')
        self._store_safely_from_cm("POSTGRES_PASSWORD", '{.metadata.annotations.postgres_password}') 
        self._store_safely_from_cm("POSTGRES_PORT", '{.metadata.annotations.postgres_port}') 
        self._store_safely_from_cm("POSTGRES_URL", '{.metadata.annotations.postgres_url}') 
        self._store_safely_from_cm("POSTGRES_USERNAME", '{.metadata.annotations.postgres_username}') 
        self._store_safely_from_cm("REDIS_PREFIX", '{.metadata.annotations.redis_prefix}')
        self._store_safely_from_cm("REDIS_URL", '{.metadata.annotations.redis_url}')
                

    def dump(self):
        logging.debug(json.dumps(self._data))

    def add_metadata(self, key: str, value: str):
        """
        append an entry to the metadata with this structure {"key":key, "value":value}
        """
        logging.debug(f"adding ({key}={value})")
        self._data['metadata'].append({"key":key, "value":value})

    def get_metadata(self):
        return self._data
    

