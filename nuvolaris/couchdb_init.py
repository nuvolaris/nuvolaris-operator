import os
import requests as req
from jinja2 import Environment, FileSystemLoader

db_protocol   = os.environ.get("DB_PROTOCOL", "http")
db_prefix     = os.environ.get("DB_PREFIX", "test_") 
db_host       = os.environ.get("DB_HOST", "localhost")
db_username   = os.environ.get("COUCHDB_USER",  "whisk_admin")
db_password   = os.environ.get("COUCHDB_PASSWORD", "some_passw0rd")
db_port       = os.environ.get("DB_PORT", "5984")
db_prefix     = "nuvolaris_"

db_base = f"{db_protocol}://{db_username}:{db_password}@{db_host}:{db_port}/"
db_auth = f"{db_base}{db_prefix}subjects"

loader = FileSystemLoader(["./nuvolaris/templates", "./nuvolaris/files"])
env = Environment(loader=loader)

def sample_request():
  return req.get(db_base).text

def sample_expand(username, password):
  return env.get_template("createUser.json").render(item={
    "value": {
      "user": username,
      "pass": password 
    }
  })

def init(secrets):
  print("SAMPLE EXPAND")
  [ [username, password] ] = list(secrets["couchdb"].items())
  print(sample_expand(username=username, password=password))
  # implement here orig/initdb.yml
  print("SAMPLE REQUEST", sample_request())

if __name__ == "__main__":
  import yaml
  secrets = yaml.safe_load(open("tests/operator-obj.yaml"))["spec"]
  init(secrets)
