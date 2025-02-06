ARG PLATFORM=linux/amd64

FROM --platform=${PLATFORM} python:3.12-alpine

RUN apk add --no-cache gcc python3-dev musl-dev linux-headers

RUN mkdir /app
WORKDIR /app
COPY requirements /app/requirements/

RUN pip install -r requirements/requirements.txt \
    -r requirements/dev.txt -r requirements/pandas.txt \
    -r requirements/polars.txt \
     && pip install ipykernel jupyterlab notebook

COPY . .

RUN pip install .

CMD ["python"]
