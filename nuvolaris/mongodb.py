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
#
# Deploys mongodb for nuvolaris using operator or standalone
# implementation.
#
# By default standalone configuration is used unless mongodb.useOperator is set to true
#
import nuvolaris.config as cfg
import nuvolaris.util as util
import nuvolaris.mongodb_operator as operator
import nuvolaris.mongodb_standalone as standalone
import logging

def create(owner=None):
    """
    Deploys the mongodb operator and wait for the operator to be ready.
    """
    useOperator = cfg.get('mongodb.useOperator') or False

    if useOperator:
        logging.info("*** creating mongodb using operator mode") 
        return operator.create(owner)

    logging.info("*** creating mongodb using standalone mode") 
    return standalone.create(owner)

def delete():
    useOperator = cfg.get('mongodb.useOperator') or False

    if useOperator:
        return operator.delete()

    return standalone.delete()    

def init():
    return "TODO"