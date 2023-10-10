import os
import base64
import random
import string
import mimetypes
import io

import common.minio_util as mutil
import common.util as ut

from common.authorize import Authorize

def build_error(message: str):
    return {
        "statusCode": 400,
        "body": message
    }

def build_response(filename, content_type, buffer):
    return {
        "statusCode": 200,
        "headers": {"Content-Type":content_type, "Content-Disposition": f"inline; filename='{filename}'"},
        "body": buffer.getvalue().decode()
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
        upload_data['path']=path_params.replace(f"{upload_data['bucket']}/","")

        file_elements = upload_data['path'].split("/")

        if len(file_elements) > 1:
           upload_data['filename']=file_elements[len(file_elements)-1]
        else:
           upload_data['filename']=file_elements

    return upload_data


def main(args):
    """
    Action implementing a generic download wrapper for the nuv devel plugin. The invoker must provide a x-impersonate-auth header containing the Openwhisk BASIC authentication of the wsku/user the action should impersonate 
    when calling this action. The upload action it is supposed to receive a path param similar to /<bucket>/<path>
    and will attempt to retrieve the given path under the given MINIO <bucket>. The bucket must exists and the impersonated user must have read permission on it.
    """
    headers = args['__ow_headers']
    if('x-impersonate-auth' not in headers):
        return build_error("invalid request, missing mandatory header: x-impersonate-auth")

    try:        
        download_data = process_path_param(args['__ow_path'])

        if 'bucket' not in download_data and 'filename' not in download_data:
            return build_error("invalid request, bucket and/or filename path error")
        
        print(f"processing request to download {download_data['path']} from bucket {download_data['bucket']}")
        user_data = Authorize(args['couchdb_host'],args['couchdb_user'],args['couchdb_password']).login(headers['x-impersonate-auth'])                   

        mo_client = mutil.build_mo_client(ut.get_env_value(user_data,"MINIO_HOST"), ut.get_env_value(user_data,"MINIO_PORT"),ut.get_env_value(user_data,"MINIO_ACCESS_KEY")  , ut.get_env_value(user_data,"MINIO_SECRET_KEY"))

        # see https://urllib3.readthedocs.io/en/latest/reference/urllib3.response.html for the format       
        response = mo_client.get_object(bucket_name = download_data['bucket'], object_name= download_data['path'])
                
        content_type = response.getheader('Content-Type')
        buffer = io.BytesIO()

        for d in response.stream():
            buffer.write(d)

        return build_response(download_data['filename'], content_type, buffer)        
    except Exception as e:       
        return build_error(f"failed to execute nuv devel command. Reason: {e}")
    finally:
        if response:
            response.close()
            response.release_conn()
