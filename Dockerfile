ARG PLATFORM=linux/amd64

FROM --platform=${PLATFORM} python:3.9-alpine

COPY . .

RUN pip install -r requirements.txt && pip install ipykernel

CMD ["python"]
