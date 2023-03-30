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
# this module wraps mc minio client using admin credentials 
# to perform various operations

import logging
import json
import subprocess
import nuvolaris.config as cfg
import nuvolaris.template as ntp
import nuvolaris.util as util
import os

class MinioClient:
    
    def __init__(self):
        self.minio_api_host   = cfg.get("minio.host", "MINIO_API_HOST", "minio")
        self.minio_api_port   = cfg.get("9000", "MINIO_API_PORT", "9000")        
        self.admin_username   = cfg.get("minio.nuvolaris.root-user", "MINIO_ADMIN_USER", "minio")
        self.admin_password   = cfg.get("minio.nuvolaris.root-password", "MINIO_ADMIN_PASSWORD", "minio123")
        self.minio_api_url   = f"http://{self.minio_api_host}:{self.minio_api_port}"
        self.alias = "local"        

        # automatically adds the local alias to mc configuration to operate on nuvolaris main MINIO server
        self.mc("alias","set", self.alias, self.minio_api_url, self.admin_username, self.admin_password)

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

    def add_user(self, username, secret_key):
        """
        adds a new minio user to the configured minio instance
        """
        res = util.check(self.mc("admin","user","add", self.alias, username, secret_key),"add_user",True)
        return util.check(self.init_namespace_alias(username, secret_key),"init_namespace_alias",res)

    def remove_user(self, username):
        """
        removes a minio user to the configured minio instance
        """
        res = util.check(self.mc("admin","user","remove", self.alias, username),"remove_user",True)
        return util.check(self.remove_namespace_alias(username),"remove_namespace_alias",res)

    def make_bucket(self, bucket_name):
        """
        adds a new bucket inside the configured minio instance 
        """
        return util.check(self.mc("mb",f"{self.alias}/{bucket_name}"),"make_bucket",True)

    def force_bucket_remove(self, bucket_name):
        """
        removes unconditionally a bucket
        """
        return util.check(self.mc("rb","--force",f"{self.alias}/{bucket_name}"),"force_bucket_remove",True)        

    def make_public_bucket(self, bucket_name):
        """
        adds a new public bucket to the configured minio instance 
        """
        res = util.check(self.make_bucket(bucket_name),"make_bucket",True)
        return util.check(self.mc("anonymous","-r","set","download",f"{self.alias}/{bucket_name}"),"make_public_bucket",res)

    def assign_policy_to_user(self, username, policy):
        """
        assign the specified policy to the given username
        """        
        return util.check(self.mc("admin","policy","attach",self.alias,policy,"--user", username),"assign_policy_to_user",True)

    def add_policy(self, policy, path_to_policy_json):
        """
        add a new policy into minio
        """        
        return util.check(self.mc("admin","policy","create",self.alias,policy,path_to_policy_json),"add_policy",True)        

    def remove_policy(self, policy):
        """
        add a new policy into minio
        """        
        return util.check(self.mc("admin","policy","remove",self.alias,policy),"remove_policy",True)

    def render_policy(self,username,template,data):
        """
        uses the given template policy to render a final policy and returns the absolute path to rendered policy file.
        """  
        out = f"/tmp/__{username}_{template}"
        file = ntp.spool_template(template, out, data)
        return os.path.abspath(file)
    
    def assign_rw_bucket_policy_to_user(self,username,bucket_names):
        """
        defines a rw policy template for the specified bucket and assigns it to the given username.
        """          
        policy_name = f"{username}_rw_policy"
        path_to_policy_json = self.render_policy(username,"minio_rw_policy_tpl.json",{"bucket_arns":bucket_names})
        res=util.check(self.add_policy(policy_name,path_to_policy_json),"add_policy",True)
        res=util.check(self.assign_policy_to_user(username,policy_name),"assign_rw_bucket_policy_to_user",res)
        os.remove(path_to_policy_json)
        return res

    def delete_user(self,username):
        """
        removes the user and the corresponding policy
        """          
        policy_name = f"{username}_rw_policy"        
        res=util.check(self.remove_user(username),"removed_user",True)
        return util.check(self.remove_policy(policy_name),"deleted_user_policy",res)

    def init_namespace_alias(self, namespace, secret_key):
        """
        called to initialize a local minio alias for a namespace user (used to impersonate the user uploading content)
        """                 
        return util.check(self.mc("alias","set", f"local_{namespace}", self.minio_api_url, namespace, secret_key),"init_namespace_alias_call",True)

    def remove_namespace_alias(self, namespace):
        """
        called to initialize to remove a local minio alias for a namespace user
        """                 
        return util.check(self.mc("alias","remove",f"local_{namespace}"),"remove_namespace_alias_call",True)

    def upload_folder_content(self,origin,bucket):
        """
        uploads the given content using a local alias for the corresponding namespace
        """
        return util.check(self.mc("cp","-r",origin,f"{self.alias}/{bucket}"),"upload_folder_content",True)



