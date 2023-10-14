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

import os
import base64
import random
import string
import mimetypes

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource

def extract_mimetype(file):
    mimetype, _ = mimetypes.guess_type(file)
        
    if mimetype is None:
       return "application/octet-stream"
    else:
        return mimetype

def build_mo_client(host, port, access_key, secret_key):
    """
    Creates an Minio client pointing to the given MINIO HOST
    :param host, minio host
    :param port, minio api port normally it is the 9000
    :param access_key user we are representing
    :param secret_key to access minio
    """
    mo_client = Minio(f"{host}:{port}",access_key=access_key,secret_key=secret_key,secure=False)    
    return mo_client

def upload_file(mo_client, file, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: a tuple with the Booleand str,
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file)

    print(f"uploading {object_name} into bucket {bucket} from tmp_file {file}")    

    # Upload the file
    try:
        mimetype = extract_mimetype(object_name)
        response = mo_client.fput_object(bucket_name=bucket,object_name=object_name,file_path=file,content_type=mimetype)
        if response._object_name:
            return True, response._object_name
    except Exception as e:
        print(e)
        return False, str(e)
    return False, "KO"

def prepare_file_upload(username, filename, file_content_as_b64):
    """ Creates a tmp area for the given user where the uploaded file will be stored under a random generated name
        the fully qualified filename is taken into account only on the corresponding destination bucket.
    param: username
    param: filename
    param: file_content_as_b64
    return: a file object pointing to the tmp file
    """
    try:        
        user_tmp_folder = f"/tmp/{username}"
        if not os.path.exists(user_tmp_folder):
            os.makedirs(user_tmp_folder)
            print(f"added tmp folder {user_tmp_folder}")

        delete_files_in_directory_and_subdirectories(user_tmp_folder)
        rnd_filename = get_random_string(20)
        tmp_file = f"{user_tmp_folder}/{rnd_filename}"
        
        with open(tmp_file, "wb") as f:
            file_content=base64.b64decode(file_content_as_b64)          
            f.write(file_content)

        if os.path.exists(tmp_file):
            print(f"{tmp_file} stored successfully.")
            return tmp_file
        else:
            return None
    except Exception as e:
        print("error preparing tmp_files",e)
        return None

def delete_files_in_directory_and_subdirectories(directory_path):
   try:
     for root, dirs, files in os.walk(directory_path):
       for file in files:
         file_path = os.path.join(root, file)
         os.remove(file_path)
     print("All files and subdirectories deleted successfully.")
   except OSError:
     print("Error occurred while deleting files and subdirectories.")   

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

def rm_file(mo_client, bucket, file):
    """ Remove a file from a bucket
    :parma mo_client a minio client instance to execute the command
    :param bucket the bucket name
    :param file the file name
    :return True if the file has been removed, False otherwise
    """
    
    try:
        mo_client.remove_object(bucket, file)
        return True
    except Exception as e:
        print(e)
        return False
    return False 

def cp_file(mo_client, orig_bucket, orig_file, dest_bucket, dest_file):
    """Copy a file between two buckets

    :param orig_bucket: Origin bucket
    :param orig_file: Origin file
    :param dest_bucket: Destination bucket
    :param dest_file: Destination file
    :return: name of the destination file is everything is ok. None otherwise
    """
    print(f"**** moving file {orig_file} from bucket {orig_bucket} to bucket {dest_bucket} with name {dest_file}")
    try:
        # copy an object from a bucket to another.
        cp_result = mo_client.copy_object(
            dest_bucket,
            dest_file,
            CopySource(orig_bucket, orig_file)
        )
        if cp_result.object_name:            
            return cp_result.object_name
    except Exception as e:
        print(e)
        return None
    return None  

def mv_file(mo_client, orig_bucket, orig_file, dest_bucket, dest_file):
    """Move a file between two buckets

    :param orig_bucket: Origin bucket
    :param orig_file: Origin file
    :param dest_bucket: Destination bucket
    :param dest_file: Destination file
    :return: name of the destination file is everything is ok. None otherwise
    """
    print(f"**** moving file {orig_file} from bucket {orig_bucket} to bucket {dest_bucket} with name {dest_file}")

    # Upload the file
    try:
        # mv an object from a bucket to another.
        object_name = cp_file(mo_client, orig_bucket, orig_file, dest_bucket, dest_file)
        if object_name:
            rm_file(mo_client,orig_bucket,orig_file)          
            return object_name
    except Exception as e:
        print(e)
        return None
    return None                             

