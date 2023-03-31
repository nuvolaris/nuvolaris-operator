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
import os, re

from jinja2 import Environment, FileSystemLoader
loader = FileSystemLoader(["./nuvolaris/templates", "./nuvolaris/files", "./nuvolaris/policies"])
env = Environment(loader=loader)

# expand template
def expand_template(template, data):
    """
    >>> import json
    >>> json.loads(expand_template("test.json", {"item": "hello"}))
    {'_id': 'test', 'value': 'hello'}
    """
    tpl = env.get_template(template)
    return tpl.render(data)
    #doc = json.loads(tpl.render(data))


# expond template and save in a file
def spool_template(template, file, data):
    """
    >>> import nuvolaris.testutil as tu
    >>> tu.grep(tu.fread(spool_template("test.json", "/tmp/test.json", {"item": "hi"})), r"value")
    "value": "hi"
    """
    with open(file, "w") as f:
        f.write(expand_template(template, data))
    return file


# expand a line of a .tpl.yml interpreting '#' comments as follows:
# if there is #!, the entire line will be removed
# if there is a #:, the part from : and #: including the #: but not the initial : will be removed, exposing the value follwing #:
# if there is a #-, the part from - and #- including the #- but not the initial - will be removed, exposing the value follwing -
# if there is a ##, the ##  (and an eventual space after) will be removed, exposing the template directive
# note only one of those comments will be executed and matched in this order
# you can escape the #x replacement rules writing #\~, #\#, #\-, #\:
# those sequences will be replaced with #~ ## #- #: respectively after the replacement
def process_tpl_line(line):
    """
    >>> line = "##{{ if some-condition }}"
    >>> print(process_tpl_line(line))
    {{ if some-condition }}
    >>> line = "  ##{{foreach item value}}"
    >>> print(process_tpl_line(line))
      {{foreach item value}}
    >>> line = "  key: value #: {{value}}"
    >>> print(process_tpl_line(line))
      key: {{value}}
    >>> line = "  - item #- {{item}}"
    >>> print(process_tpl_line(line))
      - {{item}}
    >>> line = "#\! with #\~, #\: and #\- but not #\@" 
    >>> print(process_tpl_line(line))
    #! with #~, #: and #- but not #\@
    """
    if re.search(r"#~", line):
        return ""
    elif re.search(r"##", line):
        line = re.sub(r"##(.*)$", r"\1", line, count=1)
    elif re.search(r"#:", line):
        line = re.sub(r":.*#:(.*)$", r":\1", line, count=1)
    elif re.search(r"#-", line):
        line = re.sub(r"-.*#-(.*)$", r"-\1", line, count=1)
    line = re.sub(r"#\\([!#-:~])", r"#\1", line)
    return line

