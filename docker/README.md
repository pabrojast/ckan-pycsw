# ckan-pycsw testing Environments
This repository contains a `docker` directory with various Dockerfiles for different environments such as RHEL, SUSE, Debian, etc. These Dockerfiles are designed to test the `ckan-pycsw` software in a clean, isolated, and volatile environment.

## Why Docker?
Docker allows us to create lightweight and isolated environments, known as containers, where we can run our software with all its dependencies. This makes it easy to test our software in different environments without having to install and configure each environment manually.

## What is ckan-pycsw?
`ckan-pycsw` is a software that allows CKAN data portals to publish metadata to CSW catalogs. It is written in Python 3.

## How to use these Dockerfiles?
To use these Dockerfiles, you need to have Docker installed on your machine. Once you have Docker installed, you can build a Docker image for a specific environment and run a container from that image.

Here is an example of how to build a Docker image for Debian and run a container from that image:

```bash
# Edit .env vars and select OS
vi .env

# To build the images:
docker compose -f docker-compose.test-docker.yml build

# To start the container:
docker compose -f docker-compose.test-docker.yml up
```