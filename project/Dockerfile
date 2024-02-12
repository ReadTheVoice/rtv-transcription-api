# pull official base image
FROM python:3.10.8-slim-buster

# set working directory
RUN mkdir -p /usr/app/project
WORKDIR /usr/app/

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update \
  && apt-get -y install netcat gcc \
  && apt-get -y install curl \
  && apt-get clean

# install python dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt ./project
RUN pip install -r project/requirements.txt

# add app in project directory
COPY . ./project