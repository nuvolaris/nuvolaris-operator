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
# this module wraps mc minio client

import logging
import json
import subprocess
import nuvolaris.config as cfg
import nuvolaris.template as ntp
import os

class MinioClient:
    
    def __init__(self):
        self.minio_api_host   = cfg.get("minio.host", "MINIO_API_HOST", "localhost")
        self.minio_api_port   = cfg.get("9000", "MINIO_API_PORT", "9000")        
        self.admin_username   = cfg.get("minio.nuvolaris.root-user", "MINIO_ADMIN_USER", "minioadmin")
        self.admin_password   = cfg.get("minio.nuvolaris.root-password", "MINIO_ADMIN_PASSWORD", "minioadmin")
        self.minio_api_url   = f"http://{self.minio_api_host}:{self.minio_api_port}"
        self.alias = "local"        

        # automatically adds the nuv_minio alias to map the deployed minio instance
        self.mc("alias","set", self.alias, self.minio_api_url, self.admin_username, self.admin_password)

    def check(self,f, what, res):
        if f:
            logging.info(f"OK: {what}")
            return res and True
        else:
            logging.warn(f"ERR: {what}")
            return False        

    # execute minio commands using the mc cli tools installed by default inside the operator
    def mc(self, *kwargs):        
        cmd = ["mc"]
        cmd += list(kwargs)

        # executing
        logging.debug(cmd)
        try:
            res = subprocess.run(cmd, capture_output=True)

            returncode = res.returncode
            output = res.stdout.decode()
            error = res.stderr.decode()
            
            if returncode != 0:
                logging.error(error)
            else:
                logging.info(output)

            return returncode == 0
        except Exception as e:
                        logging.error(e)
                        return e

    def add_user(self, username, access_secret):
        """
        adds a new minio user to the configured minio instance
        """
        return self.check(self.mc("admin","user","add", self.alias, username, access_secret),"add_user",True)

    def make_bucket(self, bucket_name):
        """
        adds a new bucket inside the configured minio instance 
        """
        return self.check(self.mc("mb",f"{self.alias}/{bucket_name}"),"make_bucket",True)

    def make_public_bucket(self, bucket_name):
        """
        adds a new public bucket to the configured minio instance 
        """
        res = self.check(self.make_bucket(bucket_name),"make_bucket",True)
        return self.check(self.mc("anonymous","-r","set","download",f"{self.alias}/{bucket_name}"),"make_public_bucket",res)

    def assign_policy_to_user(self, username, policy):
        """
        assign the specified policy to the given username
        """        
        return self.check(self.mc("admin","policy","set",self.alias,policy,f"user={username}"),"assign_policy_to_user",True)

    def add_policy(self, policy, path_to_policy_json):
        """
        add a new policy into minio
        """        
        return self.check(self.mc("admin","policy","add",self.alias,policy,path_to_policy_json),"add_policy",True)        

    def remove_policy(self, policy):
        """
        add a new policy into minio
        """        
        return self.check(self.mc("admin","policy","remove",self.alias,policy),"remove_policy",True)

    def render_policy(self,bucket,template,data):
        """
        uses the given template policy to render a final policy and returns the absolute path to rendered policy file.
        """  
        out = f"/tmp/__{bucket}_{template}"
        file = ntp.spool_template(template, out, data)
        return os.path.abspath(file)
    
    def assign_rw_bucket_policy_to_user(self,username,bucket_name):
        """
        defines a rw policy template for the specified bucket and assigns it to the given username.
        """          
        policy_name = f"{username}_{bucket_name}_rw_policy"
        path_to_policy_json = self.render_policy(bucket_name,"minio_rw_policy_tpl.json",{"bucket_arn":f"{bucket_name}/*"})        
        res=self.check(self.add_policy(policy_name,path_to_policy_json),"add_policy",True)
        res=self.check(self.assign_policy_to_user(username,policy_name),"assign_rw_bucket_policy_to_user",res)
        os.remove(path_to_policy_json)
        return res



