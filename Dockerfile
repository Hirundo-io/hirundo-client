FROM --platform=linux/amd64 python:3.9-alpine

COPY . .

RUN pip install -r requirements.txt

CMD ["python"]
