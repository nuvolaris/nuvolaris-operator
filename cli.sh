#!/bin/bash
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
export CONTROLLER_IMAGE=$(awk -F= '/ENV CONTROLLER_IMAGE=/ { print $2 ; exit }' Dockerfile)
export CONTROLLER_TAG=$(awk -F= '/ENV CONTROLLER_TAG=/ { print $2 ; exit }' Dockerfile)
# get operator tag from environment variables or from dockerfile
test -e .env && source .env
if test -n "$MY_OPERATOR_IMAGE"
then export OPERATOR_IMAGE=$MY_OPERATOR_IMAGE
else export OPERATOR_IMAGE=$(awk -F= '/ARG OPERATOR_IMAGE_DEFAULT=/ { print $2 ; exit }' Dockerfile)
fi
# get operator tag from environment variable or from the current tag
if test -z "$OPERATOR_TAG"
then export OPERATOR_TAG=$(git describe --tags --abbrev=0)
fi
# run the cli
poetry run ipython -i profile.ipy
