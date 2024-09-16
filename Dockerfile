ARG PLATFORM=linux/amd64

FROM --platform=${PLATFORM} python:3.9-alpine

COPY . .

RUN apk add --no-cache gcc python3-dev musl-dev linux-headers

RUN pip install -r requirements.txt && pip install ipykernel

CMD ["python"]
