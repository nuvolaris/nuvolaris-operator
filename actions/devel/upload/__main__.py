import os
import base64
import random
import string
import mimetypes

import common.minio_util as mutil
import common.util as ut

from common.authorize import Authorize

def build_error(message: str):
    return {
        "statusCode": 400,
        "body": message
    }

def build_response(user, filename,bucket, upload_result, upload_message):
    body = {
        "user":user,
        "filename":filename,
        "bucket":bucket,
        "uploaded": upload_result
    }

    if upload_message:
        body['message']=upload_message

    return {
        "statusCode": upload_result and 200 or 400,
        "body": body
    }


def process_path_param(ow_path: str):
    """ Process the __ow_path parameters to extract username and fully qualified filename

    :parma ow_path, the __ow_path parameter passed by openwhisk action controller
    :return a dictionary {bucket:<bucket>, filename:<filepath>}
    """
    path_params = ow_path
    if ow_path.startswith("/"):
        path_params = ow_path[1:None]

    path_elements = path_params.split("/")

    upload_data = {}

    if len(path_elements) >= 1:
        upload_data['bucket']=path_elements[0]
        upload_data['filename']=path_params.replace(f"{upload_data['bucket']}/","")

    return upload_data


def main(args):
    """
    Action implementing a generic upload wrapper for the nuv devel plugin. The invoker must provide a x-impersonate-auth header containing the Openwhisk BASIC authentication of the wsku/user the action should impersonate 
    when calling this action. The upload action it is supposed to receive a path param similar to /<bucket>/<path>
    and will store the given path under the given MINIO <bucket>. The bucket must exists and the impersonated user must have write permission on it.
    """
    headers = args['__ow_headers']
    if('x-impersonate-auth' not in headers):
        return build_error("invalid request, missing mandatory header: x-impersonate-auth")
    
    if(len(args['__ow_body']) == 0):
        return build_error("invalid request, no file content has been received")

    try:        
        upload_data = process_path_param(args['__ow_path'])

        if 'bucket' not in upload_data and 'filename' not in upload_data:
            return build_error("invalid request, bucket and/or filename path error")
        
        content_as_b64 = args['__ow_body']

        user_data = Authorize(args['couchdb_host'],args['couchdb_user'],args['couchdb_password']).login(headers['x-impersonate-auth'])                   
        print(f"processing request to upload file {upload_data['filename']}")

        mo_client = mutil.build_mo_client(ut.get_env_value(user_data,"MINIO_HOST"), ut.get_env_value(user_data,"MINIO_PORT"),ut.get_env_value(user_data,"MINIO_ACCESS_KEY")  , ut.get_env_value(user_data,"MINIO_SECRET_KEY"))
        tmp_file = mutil.prepare_file_upload(user_data['login'],upload_data['filename'],content_as_b64)

        if tmp_file:        
            upload_result, upload_message = mutil.upload_file(mo_client,tmp_file,upload_data['bucket'],upload_data['filename'])
            return build_response(user_data['login'],upload_data['filename'],upload_data['bucket'],upload_result, upload_message)
        else:
            return build_error("Unexptected error upload action. Check activation log")
    except Exception as e:        
        return build_error(f"failed to execute nuv devel command. Reason: {e}")
