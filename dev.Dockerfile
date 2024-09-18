ARG PLATFORM=linux/amd64

FROM --platform=${PLATFORM} mcr.microsoft.com/devcontainers/python:3.9

COPY . .

RUN pip install -r requirements.txt && pip install ipykernel

CMD ["python"]
