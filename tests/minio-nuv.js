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
const Minio = require('minio');

async function main(args) {        
    console.log(`connecting to ${args.minio_host}:${args.minio_port}`)
    let minioClient = new Minio.Client({
        endPoint: args.minio_host,
        port: args.minio_port,
        useSSL: false,
        accessKey: args.minio_access,
        secretKey: args.minio_secret
    });

    let response = {};
    let bucketName = args.minio_data;

    console.log(`checking existence of bucket ${bucketName}`)
    let bucketExists = await minioClient.bucketExists(bucketName);
    console.log(`bucket ${bucketName} exists ${bucketExists}`)

    if(!bucketExists) {
        console.log(`creating missing bucket ${bucketName}`)       
        response.bucketOperation = await  minioClient.makeBucket(bucketName, 'us-east-1');
    }

    response.buckets = await minioClient.listBuckets();
    return {
        "body": response
    }
}