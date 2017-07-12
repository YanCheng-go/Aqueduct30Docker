# Aqueduct 3.0 Data Processing workflow

A link to the flowchart±
https://docs.google.com/drawings/d/1IjTVlQUHNYj2w0zrS8SKQV1Bpworvt0XDp7UE2tPms0/edit?usp=sharing

![GitHub Logo](/flowchart.png)
Format: ![Alt Text](url)




this document explains each and every step for the data processing of Aqueduct 3.0. Everything is here, from raw data to code to explanation. We also epxlain how you could replicate the calculations on your local machine or in a cloud environment. 

The overall structure is as follows:

Data is stored on WRI's Amazon S3 Storage
Code and versionion is stored on Github 
The environment description is stored in a Docker file 
A jupyter notebook can be used to run the code in a virtual machine. 

For steps that do not include code, such as adding columns to a shapefile in QGIS, a description is included.  

1) Run locally

2) Run in the cloud


Instructions to run the calculations locally

install Docker






build docker:
`docker build -t <imageName> testDocker`

Run the container
docker run -d -p 8888:8888 <imageName>
or 
docker run -d -p 8888:8888 rutgerhofste/xxxx:xxx

service is running on 
http://localhost:8888




share repo on hub.docker
`docker login`
`docker tag image username/repository:tag`
e.g.: `docker tag friendlyhello rutgerhofste/get-started:part1`
`docker push username/repository:tag`





cleanup

check containers
`docker ps -a`


`docker stop <containerID>`

`docker rm <containerID>`

check images
`docker images`

`docker rmi <imageID>`

 
run with environment variables (unsafe)
docker run -e AWS_ACCESS_KEY_ID=xyz -e AWS_SECRET_ACCESS_KEY=aaa myimage


Safe way:
run bash on docker container and use AWS configure
aws configure

us-east-1


aws configure 

Copy files to volume 

aws s3 cp s3://wri-projects/Aqueduct30/temp  /volumes/data/ /volumes/data/ --recursive








