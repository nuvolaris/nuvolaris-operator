/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

{% if mode == 'create' %}
CREATE DATABASE {{database}};
CREATE USER {{username}} WITH PASSWORD '{{password}}';
GRANT ALL PRIVILEGES ON DATABASE {{database}} to {{username}};
{% endif %}

{% if mode == 'delete' %}
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '{{database}}';

DROP DATABASE {{database}};

DROP OWNED BY {{username}};
DROP USER {{username}};
{% endif %}