import os
import base64
import random
import string
import mimetypes

import common.minio_util as mutil

def build_error(message: str):
    return {
        "statusCode": 400,
        "body": message
    }

def build_response(user, filename, bucket, upload_result, operation):
    body = {
        "user":user,
        "filename":filename,
        "bucket":bucket,
        "operation": operation
    }

    return {
        "statusCode": upload_result and 200 or 400,
        "body": body
    }


def process_path_param(ow_path: str):
    """ Process the __ow_path parameters to extract username and fully qualified filename

    :parma ow_path, the __ow_path parameter passed by openwhisk action controller
    :return a dictionary {user:<user>, filename:<filepath>}
    """
    path_params = ow_path
    if ow_path.startswith("/"):
        path_params = ow_path[1:None]

    path_elements = path_params.split("/")

    upload_data = {}

    if len(path_elements) >= 1:
        upload_data['user']=path_elements[0]
        upload_data['filename']=path_params.replace(f"{upload_data['user']}/","")

    return upload_data

def _put(mo_client, upload_data, content_as_b64):
    """
    Store the given payload into a folder
    :param mo_client 
    :param upload_data 
    :param content_as_b64 file to be stored in a base64 endoded format     
    """
    print(f"processing request to upload file {upload_data['filename']} under {upload_data['user']} web-bucket")
    tmp_file = mutil.prepare_file_upload(upload_data['user'],upload_data['filename'],content_as_b64)

    if tmp_file:        
        upload_result, upload_message = mutil.upload_file(mo_client,tmp_file,f"{upload_data['user']}-web",upload_data['filename'])
        return build_response(upload_data['user'],upload_data['filename'],f"{upload_data['user']}-web",upload_result,"PUT")
    else:
        return build_error("Unexptected error content action. Check activation log")  

def _delete(mo_client, upload_data):
    print(f"processing request to remove file {upload_data['filename']} under {upload_data['user']} web-bucket")
    removed = mutil.rm_file(mo_client,f"{upload_data['user']}-web", upload_data['filename'])

    if removed:                
        return build_response(upload_data['user'],upload_data['filename'],f"{upload_data['user']}-web",removed,"DELETE")
    else:
        return build_error("Unexptected error content action. Check activation log")  

def main(args):
    """
    Simple actions to upload/remove a files into a minio bucket.
    The action it is supposed to receive a path param similar to /<user>/<path>?<auth>
    and will store/remove the given path under the <user>-web bucket using minio client
    """
    print(args)

    method = args['__ow_method']
    headers = args['__ow_headers']

    if(method.lower() not in ['put','delete'] ):
        return build_error(f"invalid request, HTTP verb {method} is not supported")
    
    if('minioauth' not in headers):
        return build_error("invalid request, missing mandatory header: minioauth")
    
    upload_data = process_path_param(args['__ow_path'])

    if 'user' not in upload_data and 'filename' not in upload_data:
        return build_error("invalid request, username and/or filename path error")
    
    minio_host = args['minio_host']
    minio_port = args['minio_port']       
    auth = headers['minioauth']

    mo_client = mutil.build_mo_client(minio_host, minio_port,upload_data['user'], auth)

    if method.lower() in 'put':
        if(len(args['__ow_body']) == 0):
            return build_error("invalid request, no file content has been received")
    
        content_as_b64 = args['__ow_body']
        return _put(mo_client, upload_data, content_as_b64)
    
    if method.lower() in 'delete':
        return _delete(mo_client, upload_data)
