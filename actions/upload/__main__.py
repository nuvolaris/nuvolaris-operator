import os
import base64
import random
import string
import mimetypes

from minio import Minio
from minio.error import S3Error

def build_error(message: str):
    return {
        "statusCode": 400,
        "body": message
    }

def build_response(user, filename,bucket, upload_result):
    body = {
        "user":user,
        "filename":filename,
        "bucket":bucket,
        "uploaded": upload_result
    }

    return {
        "statusCode": upload_result and 200 or 400,
        "body": body
    }

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

def extract_mimetype(file):
    mimetype, _ = mimetypes.guess_type(file)
    if mimetype is None:
        raise Exception(f"Failed to guess mimetype for {file}")
    else:
        return mimetype    
            
def upload_file(mo_client, file, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
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
            return True
    except Exception as e:
        print(e)
        return False
    return False

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

def main(args):
    """
    Simple actions to upload a files into a minio bucket.
    The upload action it is supposed to receive a path param similar
    /<user>/<path>?<auth>
    and will store the given path under the <user>-web bucket using mnio
    """
    print(args)

    headers = args['__ow_headers']
    if('minioauth' not in headers):
        return build_error("invalid request, missing mandatory header: minioauth")
    
    if(len(args['__ow_body']) == 0):
        return build_error("invalid request, no file content has been received")
    
    upload_data = process_path_param(args['__ow_path'])

    if 'user' not in upload_data and 'filename' not in upload_data:
        return build_error("invalid request, username and/or filename path error")
    
    minio_host = args['minio_host']
    minio_port = args['minio_port']    
    content_as_b64 = args['__ow_body']
    auth = headers['minioauth']
    
    print(f"processing request to upload file {upload_data['filename']} under {upload_data['user']} web-bucket")

    mo_client = build_mo_client(minio_host, minio_port,upload_data['user'], auth)
    tmp_file = prepare_file_upload(upload_data['user'],upload_data['filename'],content_as_b64)

    if tmp_file:        
        upload_result = upload_file(mo_client,tmp_file,f"{upload_data['user']}-web",upload_data['filename'])
        return build_response(upload_data['user'],upload_data['filename'],f"{upload_data['user']}-web",upload_result)
    else:
        return build_error("Unexptected error upload action. Check activation log")