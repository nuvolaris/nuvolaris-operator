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
import logging, re

def duration_in_second(string):
    """
    Conveniently parse a string represting a finite time unit in multiple format (s, m, h, d, sec, min, hour, day) and convert it into seconds.    
    >>> import nuvolaris.time_util as tu
    >>> tu.duration_in_second("1s")        
    1
    >>> tu.duration_in_second("1m")        
    60
    >>> tu.duration_in_second("1h")        
    3600
    >>> tu.duration_in_second("1d")    
    86400
    >>> tu.duration_in_second("1 s")
    1
    >>> tu.duration_in_second("1 d")
    86400
    >>> tu.duration_in_second("1 sec")
    1
    >>> tu.duration_in_second("1 min")
    60
    >>> tu.duration_in_second("1 hour")
    3600
    >>> tu.duration_in_second("1 day")
    86400
    >>> tu.duration_in_second("5  min")
    300
    >>> tu.duration_in_second("5min")
    300
    >>> tu.duration_in_second("10  min")
    600
    """
    mult = {"s": 1, "m": 60, "h": 60*60, "d": 60*60*24,"sec": 1, "min": 60, "hour": 60*60, "day": 60*60*24}
    parts = re.findall(r"(\d+(?:\s+)?)([\w])", string)
    total_seconds = sum(int(x) * mult[m] for x, m in parts)
    return total_seconds