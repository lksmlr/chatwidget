# KIWI

## Getting Started

1. Clone the repos with ssh or https. If u want to use ssh u need to add an api key to GitLab. 

ssh: git@git.informatik.fh-nuernberg.de:muellerlu93279/kiwi-ki-chatbot-widget.git

https: https://git.informatik.fh-nuernberg.de/muellerlu93279/kiwi-ki-chatbot-widget.git

2. Install Python 3.12 and add it to your environment variables. Create an environment with python -m venv kiwi-venv

3. activate the venv. Its different on Linux and Windows

4. install the requirements under requirements/requirements.txt

## structure

The folders under src are all services except the clients. The services are all build with seperate docker images. They are based under Dockerfiles. The clients are the handy way for using the services. 

admin service -> the admin service is the admin panel for the admin

dense service -> the dense service is for calculating the dense embeddings

ingest service -> ingest means "hinzufügen" in german. So its the endpoint for insert new urls and documents to the veectorstore

sparse service -> the sparse service is for calculating the sparse embeddings

widget service -> its the main application

## Docker

Every docker image ist located in Dockerhub. The base image is also located there. The base image contains the requirements from pip. If the requirements change, u have to build the base image first. 

admin ->    1. sudo docker pull lksmler/admin
            2. sudo docker run -p 8000:8000 lksmler/admin

dense ->    1. sudo docker pull lksmler/dense
            2. sudo docker run -p 8400:8400 lksmler/dense

ingest ->   1. sudo docker pull lksmler/ingest
            2. sudo docker run -p 8600:8600 -v /path/to/model:/model lksmler/ingest

sparse ->   1. sudo docker pull lksmler/sparse
            2. sudo docker run -p 8500:8500 lksmler/sparse

widget ->   1. sudo docker pull lksmler/widget
            2. sudo docker run -p 8080:8080 lksmler/widget

