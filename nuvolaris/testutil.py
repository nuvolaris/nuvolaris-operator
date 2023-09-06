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
import yaml
import re
import flatdict
import json
import time
import os
import requests as req
from subprocess import run
from urllib.parse import urlparse
import uuid
import string
import random

# takes a string, split in lines and search for the word (a re)
# if field is a number, splits the line in fields separated by spaces and print the selected field
# the output is always space trimmed for easier check
def grep(input, word, field=None, sort=False):
    r"""
    >>> import nuvolaris.testutil as tu
    >>> tu.grep("a\nb\nc\n", "b")
    b
    >>> tu.grep(b"a\nb\n c\n", r"a|c")
    a
    c
    >>> tu.grep(b"z\nt\n w\n", r"w|z", sort=True)
    w
    z
    """
    try: input = input.decode()
    except: pass
    lines = []
    for line in str(input).split("\n"):
        if re.search(word, line):
            line = line.strip()
            if not field is None:
                try:
                    line = line.split()[field]
                except:
                    line = "missing-field"
            lines.append(line)
    if sort:
        lines.sort()
    res = "\n".join(lines)
    print(res)


# print a file
def cat(file):
    with open(file, "r") as f:
        print(f.read())

# print a file
def fread(file):
    with open(file, "r") as f:
        return f.read()

# capture and print an exception with its type
# or just print the output of the fuction
def catch(f):
    """
    >>> import nuvolaris.testutil as tu
    >>> tu.catch(lambda: "ok")
    ok
    >>> def error():
    ...   raise Exception("error")
    >>> tu.catch(error)
    <class 'Exception'> error
    """
    try: print(f().strip())
    except Exception as e:
        print(type(e), str(e).strip())

# print not blank lines only
def nprint(out):
    for line in out.split("\n"):
        if line.strip() != "":
            print(line)

# print in yaml an obj
def yprint(obj):
    print(yaml.dump(obj))


# load an YAML file
def load_yaml(file):
    f = open(file)
    l = list(yaml.load_all(f, yaml.Loader))
    if len(l)  > 0:
        return l[0]
    return {}


# mocking and spying kube support
class MockKube:
    """
    >>> from nuvolaris.testutil import *
    >>> m = MockKube()
    >>> m.invoke()
    >>> m.config("", "ok")
    >>> m.invoke()
    'ok'
    >>> m = MockKube()
    >>> m.config("apply", "applied")
    >>> m.invoke()
    >>> m.echo()
    >>> m.invoke("apply", "-f")
    kubectl apply -f
    'applied'
    >>> m.peek()
    'apply -f'
    >>> m.dump()
    ''
    >>> m.save("hello")
    >>> m.dump()
    'hello'
    """ 
    def __init__(self):
        self.reset()

    def reset(self):
        self.map = {}
        self.queue = []
        self.saved = []
        self.echoFlag = False
        self.enabled = False

    def echo(self, flag=True):
        self.echoFlag = flag

    def peek(self, index=-1):
        res = self.queue[index][0]
        return res

    def dump(self, index=-1):
        return self.queue[index][1]

    def save(self, data, index=-1):
        self.queue[index] = (self.queue[index][0], data)

    def config(self, request, response):
        self.enabled = True
        self.map[request] = response

    def invoke(self, *args):
        if self.enabled:
            cmd = " ".join(args)
            for key in list(self.map.keys()):
                if cmd.startswith(key):
                    if self.echoFlag:
                        print("kubectl", cmd)
                    self.queue.append( (cmd,"") )
                    return self.map[key]
        return None

def load_sample_config(name="whisk"):
    with open(f"tests/{name}.yaml") as f: 
        c = yaml.safe_load(f)
        return c['spec']

# read environment variables from Dockerfile, .env and git config
def load_image_env():
    # operator images defaults in Dockerfile, can be overriden in .env
    r = run('grep "ARG OPERATOR_IMAGE_DEFAULT=" Dockerfile', shell=True, capture_output=True)
    opimg = r.stdout.strip().decode("ascii").split("=")[-1]
    r = run('grep MY_OPERATOR_IMAGE .env', shell=True, capture_output=True)
    if r.returncode == 0:
        opimg = r.stdout.strip().decode("ascii").split("=")[-1]
    os.environ["OPERATOR_IMAGE"] = opimg
    # operator tag is the git tag of the operator
    r = run('git describe --tags --abbrev=0 2>/dev/null || git rev-parse --short HEAD', shell=True, capture_output=True)
    tag = r.stdout.strip().decode("ascii")
    os.environ["OPERATOR_TAG"] = tag
    # controller images and tag are in the Dockerfile
    r = run("grep -Po '(?<=CONTROLLER_IMAGE=).*' Dockerfile", shell=True, capture_output=True)
    os.environ["CONTROLLER_IMAGE"] =  r.stdout.decode("ascii").strip()
    r = run("grep -Po '(?<=CONTROLLER_TAG=).*' Dockerfile", shell=True, capture_output=True)
    os.environ["CONTROLLER_TAG"] =  r.stdout.decode("ascii").strip()


def set_apihost_from_kubeconfig(cfg):
    # assume for k3s and microk8s, 
    # the nuvolaris apihost is the same as the kube api server
    r = run("kubectl config view -o json | jq -r '.clusters[0].cluster.server'", shell=True, capture_output=True)
    server = r.stdout.decode("ascii").strip()
    hostname = urlparse(server).hostname    
    kube = cfg.get("nuvolaris.kube")
    if kube is None:
        return
    if kube in ["k3s", "microk8s"]:
        cfg.put("nuvolaris.apihost", hostname)
    if kube == "openshift":
        hostname1 =  ".".join(["nuvolaris", "apps"] + hostname.split(".")[1:])
        cfg.put("nuvolaris.apihost", hostname1)


def json2flatdict(data):
    return dict(flatdict.FlatterDict(json.loads(data), delimiter="."))

def get_by_key_sub(dic, key):
    res = []
    for k in list(dic.keys()):
        try:
            k.index(key)
            res.append(dic[k])
        except:
            pass
    return "\n".join(res)

def read_dotenv():
    import os
    try:
        f = open(".env")
        lines = f.readlines()
        #print(lines)
        for line in lines:
            #print(line)
            #line = lines[1]
            a = line.split("=", 1)
            if len(a) == 2:
                print(a[0])
                os.environ[a[0]] = a[1].strip()
        f.close()
    except Exception as e:
        print(e)
        print(".env not found")
        pass

def get_with_retry(url, max_seconds):
    start = time.time()
    delta = 0
    while delta < max_seconds:
        try:
            r = req.get(url, timeout=1)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print(e)
            print(f"waiting since: {delta} seconds")
        delta = int(time.time() - start)
        time.sleep(1)
    return ""

# retry a function until it returns a given value
# return true when the value is what is expected, false otherwise
def retry(fn, value, max=10, delay=1):
    for i in range(0, max):
        if fn() == value:
            return True
        time.sleep(delay)
        print(i, "retrying...")
    return False

def generate_ow_uid():
    """
        >>> import nuvolaris.testutil as util        
        >>> len(util.generate_ow_uid())
        36
    """ 
    return str(uuid.uuid4())

def generate_ow_key():
    """
        >>> import nuvolaris.testutil as util        
        >>> len(util.generate_ow_key())
        64
    """ 
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(64))

def generate_ow_auth():
    """
        >>> import nuvolaris.testutil as util        
        >>> len(util.generate_ow_auth())
        101
    """     
    uid = generate_ow_uid()
    key = generate_ow_key()
    return f"{uid}:{key}"

def load_sample_user_config(name="whisk-user"):
    with open(f"tests/{name}.yaml") as f: 
        c = yaml.safe_load(f)
        return c['spec']

def load_sample_runtimes(name="runtimes"):
    with open(f"tests/{name}.json") as f: 
        return json.load(f)