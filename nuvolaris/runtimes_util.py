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
import kopf, logging, time, os
import nuvolaris.kube as kube
import nuvolaris.kustomize as kus
import nuvolaris.config as cfg
import nuvolaris.util as util

def find_default_container(containers: list, container_name, runtime_list):
    """ Scans for the inner runtime list and add an entry into the containers for the default one if any
    :param containers, the global containers array
    :param container_name, the name that will be assigned for the containers preloader
    :param runtime_list the where to find for the default runtime if any
    """
    for runtime in runtime_list:        
        if runtime['default']:
            img = runtime['image']
            container = {
                "name": container_name,
                "image": f"{img['prefix']}/{img['name']}:{img['tag']}"
                }
            containers.append(container)    

def parse_runtimes(runtimes_as_json):
    """ parse an openwhisk runtimes json and returns a stuitable data structure to customize the preloader jon
    :param runtimes_as_json a runtime json typically extracted from a config map
    >>> import nuvolaris.testutil as tutil
    >>> runtimes_as_json = tutil.load_sample_runtimes()
    >>> data = parse_runtimes(runtimes_as_json)
    >>> len(data['containers']) == 8
    True
    """
    data = {}
    containers = list()

    for name in runtimes_as_json["runtimes"]:        
        find_default_container(containers, name, runtimes_as_json["runtimes"][name])
           
    data['containers']=containers
    return data