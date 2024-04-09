FROM python:3.11-alpine

RUN mkdir -p /opt/app/project
WORKDIR /opt/app/

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./project ./project

RUN pip install --upgrade pip
RUN pip install -r project/requirements.txt

EXPOSE 8080
CMD ["uvicorn", "project.src.app.main:app", "--host", "0.0.0.0", "--port", "8080"]