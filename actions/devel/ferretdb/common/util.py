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

import mimetypes

def get_env_value(user_data, key):
    """
    Check if inside the given user_data object there is an env item with the
    given name and returns the value if any.
    :param user_data
    :param key
    :return None if the given key it is not prese
    """    
    envs = list(user_data['env'])

    for env in envs:
        if env['key'] == key:
            return env['value']

    return None  