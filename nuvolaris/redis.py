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

import nuvolaris.kustomize as kus
import nuvolaris.kube as kube
import nuvolaris.config as cfg
import urllib.parse
import os, os.path
import logging
import kopf


def create(owner=None):
    logging.info("create redis")
    vsize = int(cfg.get("couchdb.volume-size", "REDIS_VOLUME_SIZE", 0))
    data = {
        "name": "redis",
        "dir": "/redis-master-data",
        "size": vsize,
        "storageClass": cfg.get("nuvolaris.storageClass")
    }

    kust = ''
    if vsize >0:
        kust = kus.patchTemplate("redis", "set-attach.yaml", data)
    spec = kus.kustom_list("redis", kust, templates=["redis-conf.yaml"], data=data)

    if owner:
        kopf.append_owner_reference(spec['items'], owner)
    else:
        cfg.put("state.redis.spec", spec)
    res = kube.apply(spec)
    logging.info(f"create redis: {res}")
    return res


def delete():
    spec = cfg.get("state.redis.spec")
    res = False
    if spec:
        res = kube.delete(spec)
        logging.info(f"delete redis: {res}")
    return res

