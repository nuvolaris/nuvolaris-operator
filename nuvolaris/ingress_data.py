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
import os
import nuvolaris.config as cfg
import nuvolaris.util as util
import nuvolaris.kustomize as kus
import nuvolaris.time_util as tutil
import nuvolaris.template as ntp
import urllib.parse

class IngressData:
    _data = {}

    def __init__(self, apihost):
        runtime = cfg.get('nuvolaris.kube')
        tls = cfg.get('components.tls') and not runtime=='kind'

        url = urllib.parse.urlparse(apihost)
        hostname = url.hostname
        ingress_class = util.get_ingress_class(runtime)

        apply_traefik_prefix_middleware = ingress_class == 'traefik'
        apply_nginx_rewrite_rule = not apply_traefik_prefix_middleware
        
        self._data = {
            "hostname":hostname,
            "tls":tls,
            "apply_traefik_prefix_middleware": apply_traefik_prefix_middleware,
            "apply_nginx_rewrite_rule": apply_nginx_rewrite_rule,
            "ingress_class":ingress_class,
            "route_timeout_seconds":tutil.duration_in_second(util.get_controller_http_timeout())
        }

    def dump(self):
        logging.debug(json.dumps(self._data))

    def with_service_name(self,value: str):
        self._data['service_name']=value

    def with_ingress_name(self,value: str):
        self._data['ingress_name']=value

    def with_secret_name(self,value: str):
        self._data['secret_name']=value

    def with_service_port(self,value: str):
        self._data['service_port']=value 
    
    def with_context_path(self,value: str):
        self._data['context_path']=value 

    def with_path_type(self,value: str):
        self._data['path_type']=value 

    def with_rewrite_target(self,value: str):
        self._data['rewrite_target']=value

    def with_middleware_ingress_name(self, value: str):
        self._data['middleware_ingress_name']=value

    def with_needs_rewrite(self,value: bool):
        self._data['needs_rewrite']=value                                                      

    def build_ingress_spec(self, where: str, out_template, tpl = "generic-ingress-tpl.yaml"):        
        logging.info(f"*** Building ingress template using host {self._data['hostname']} endpoint for {self._data['ingress_name']} via template {tpl}")
        return kus.processTemplate(where, tpl, self._data, out_template)

    def requires_traefik_middleware(self):
        return self._data["ingress_class"] in ["traefik"]

    def render_template(self,namespace,tpl= "generic-ingress-tpl.yaml"):
        """
        uses the given template to render a final ingress template and returns the path to the template
        """
        logging.info(f"*** Rendering ingress template using host {self._data['hostname']} endpoint for {self._data['ingress_name']} via template {tpl}")  
        out = f"/tmp/__{namespace}_{tpl}"
        file = ntp.spool_template(tpl, out, self._data)
        return os.path.abspath(file)

    def render_traefik_middleware_template(self, namespace,tpl="traefik-prefix-middleware-tpl.yaml"):
        logging.info(f"*** Rendering traefik middleware template using host {self._data['hostname']} endpoint for {self._data['ingress_name']} via template {tpl}")
        """
        uses the given template policy to render a final ingress template.
        """  
        out = f"/tmp/__{namespace}_{tpl}"
        file = ntp.spool_template(tpl, out, self._data)
        return os.path.abspath(file)                     