import nuvolaris.config as cfg
import nuvolaris.couchdb_util as cu
import logging, json

USER_META_DBN = "users_metadata"

def fetch_user_data(db, login: str):
    logging.info(f"searching for user {login} data")
    try:
        selector = {"selector":{"login": {"$eq": login }}}
        response = db.find_doc(USER_META_DBN, json.dumps(selector))

        if(response['docs']):
                docs = list(response['docs'])
                if(len(docs) > 0):
                    return docs[0]
        
        logging.warn(f"Nuvolaris metadata for user {login} not found!")
        return None
    except Exception as e:
        logging.error(f"failed to query Nuvolaris metadata for user {login}. Reason: {e}")
        return None

def build_error(message: str):
    return {
        "statusCode": 400,
        "body": message
    }

def build_response(user_data):
    body = {}
    envs = list(user_data['env'])

    for env in envs:
        body[env['key']]=env['value']

    return {
        "statusCode": 200,
        "body": body
    }

def main(args):
    cfg.clean()
    cfg.put("couchdb.host", args['couchdb_host'])
    cfg.put("couchdb.admin.user", args['couchdb_user'])
    cfg.put("couchdb.admin.password", args['couchdb_password'])
    
    if('login' in args and 'password' in args):
        db = cu.CouchDB()
        login = args['login']
        password = args['password']
        user_data = fetch_user_data(db,login)

        if(user_data):
            if(password == user_data['password']):
                return build_response(user_data)
            else:
                return build_error(f"password mismatch for user {login}")
        else:
           return build_error(f"no user {login} found")
    else:
        return build_error("please provide login and password parameters")