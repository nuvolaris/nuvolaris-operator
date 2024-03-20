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
FROM ubuntu:22.04
ENV CONTROLLER_IMAGE=ghcr.io/nuvolaris/openwhisk-controller
ENV CONTROLLER_TAG=3.1.0-mastrogpt.2402101445
ARG OPERATOR_IMAGE_DEFAULT=ghcr.io/nuvolaris/nuvolaris-operator
ARG OPERATOR_TAG_DEFAULT=0.2.1-trinity.22061708
ENV OPERATOR_IMAGE=${OPERATOR_IMAGE_DEFAULT}
ENV OPERATOR_TAG=${OPERATOR_TAG_DEFAULT}

# configure dpkg && timezone
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
ENV TZ=Europe/London
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
# install Python
RUN apt-get update && apt-get -y upgrade &&\
    apt-get -y install apt-utils python3.10 python3.10-venv curl sudo telnet inetutils-ping zip unzip
# Download Kubectl
RUN KVER="v1.23.0" ;\
    ARCH="$(dpkg --print-architecture)" ;\
    KURL="https://dl.k8s.io/release/$KVER/bin/linux/$ARCH/kubectl" ;\
    curl -sL $KURL -o /usr/bin/kubectl && chmod +x /usr/bin/kubectl
RUN VER="v4.5.7" ;\
    ARCH="$(dpkg --print-architecture)" ;\
    URL="https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F$VER/kustomize_${VER}_linux_${ARCH}.tar.gz" ;\
    curl -sL "$URL" | tar xzvf - -C /usr/bin
# Download WSK
RUN WSK_VERSION=1.2.0 ;\
    WSK_BASE=https://github.com/apache/openwhisk-cli/releases/download ;\
    ARCH=$(dpkg --print-architecture) ;\
    WSK_URL="$WSK_BASE/$WSK_VERSION/OpenWhisk_CLI-$WSK_VERSION-linux-$ARCH.tgz" ;\
    curl -sL "$WSK_URL" | tar xzvf - -C /usr/bin/
# Download MINIO client
RUN rm -Rvf /tmp/minio-binaries ;\
    mkdir /tmp/minio-binaries ;\
    MINIO_BASE=https://dl.min.io/client/mc/release/linux ;\
    ARCH=$(dpkg --print-architecture) ;\
    MC_VER=RELEASE.2023-03-23T20-03-04Z ;\
    MINIO_URL="$MINIO_BASE-$ARCH/archive/mc.${MC_VER}" ;\
    curl -sL "$MINIO_URL" --create-dirs -o /tmp/minio-binaries/mc ;\
    chmod +x /tmp/minio-binaries/mc ;\
    mv /tmp/minio-binaries/mc /usr/bin/mc ;\
    rm -Rvf /tmp/minio-binaries
# Download and instal task
RUN sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/bin
# add nuvolaris user
RUN groupadd --gid 1001 nuvolaris
RUN useradd -m nuvolaris -s /bin/bash --uid 1001 --gid 1001 --groups root
RUN echo "nuvolaris ALL=(ALL:ALL) NOPASSWD: ALL" >>/etc/sudoers

#RUN useradd -m -s /bin/bash -g root -N nuvolaris && \
#    echo "nuvolaris ALL=(ALL:ALL) NOPASSWD: ALL" >>/etc/sudoers

WORKDIR /home/nuvolaris
# install the operator
ADD nuvolaris/*.py /home/nuvolaris/nuvolaris/
ADD nuvolaris/files /home/nuvolaris/nuvolaris/files
ADD nuvolaris/templates /home/nuvolaris/nuvolaris/templates
ADD nuvolaris/policies /home/nuvolaris/nuvolaris/policies
ADD deploy/nuvolaris-operator /home/nuvolaris/deploy/nuvolaris-operator
ADD deploy/nuvolaris-permissions /home/nuvolaris/deploy/nuvolaris-permissions
ADD deploy/openwhisk-standalone /home/nuvolaris/deploy/openwhisk-standalone
ADD deploy/openwhisk-endpoint /home/nuvolaris/deploy/openwhisk-endpoint
ADD deploy/couchdb /home/nuvolaris/deploy/couchdb
ADD deploy/redis /home/nuvolaris/deploy/redis
ADD deploy/scheduler /home/nuvolaris/deploy/scheduler
ADD deploy/mongodb-operator /home/nuvolaris/deploy/mongodb-operator
ADD deploy/mongodb-operator-deploy /home/nuvolaris/deploy/mongodb-operator-deploy
ADD deploy/mongodb-standalone /home/nuvolaris/deploy/mongodb-standalone
ADD deploy/cert-manager /home/nuvolaris/deploy/cert-manager
ADD deploy/ingress-nginx /home/nuvolaris/deploy/ingress-nginx
ADD deploy/issuer /home/nuvolaris/deploy/issuer
ADD deploy/minio /home/nuvolaris/deploy/minio
ADD deploy/nginx-static /home/nuvolaris/deploy/nginx-static
ADD deploy/content /home/nuvolaris/deploy/content
ADD deploy/postgres-operator /home/nuvolaris/deploy/postgres-operator
ADD deploy/postgres-operator-deploy /home/nuvolaris/deploy/postgres-operator-deploy
ADD deploy/ferretdb /home/nuvolaris/deploy/ferretdb
ADD deploy/runtimes /home/nuvolaris/deploy/runtimes
ADD deploy/postgres-backup /home/nuvolaris/deploy/postgres-backup
ADD run.sh dbinit.sh cron.sh pyproject.toml poetry.lock whisk-system.sh /home/nuvolaris/

# prepares the required folders to deploy the whisk-system actions
RUN mkdir /home/nuvolaris/deploy/whisk-system
ADD actions /home/nuvolaris/actions

USER nuvolaris
ENV PATH=/home/nuvolaris/.local/bin:/usr/local/bin:/usr/bin:/sbin:/bin
RUN curl -sSL https://install.python-poetry.org | python3.10 -
RUN poetry install
USER root
RUN chown -R nuvolaris /home/nuvolaris ;\
    chgrp -R root /home/nuvolaris ;\
    chmod -R 0775 /home/nuvolaris
USER nuvolaris
ENV HOME=/home/nuvolaris
RUN ./whisk-system.sh
RUN cd deploy && tar cvf ../deploy.tar *
CMD ./run.sh
