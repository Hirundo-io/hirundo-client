ARG PLATFORM=linux/amd64

FROM --platform=${PLATFORM} ghcr.io/prefix-dev/pixi:0.40.3-bullseye AS build

RUN mkdir /app
WORKDIR /app
COPY requirements /app/requirements/

RUN pixi init --format pyproject && pixi add python==3.13 && \
    pixi add gcc gxx pkg-config && \
    pixi add --pypi $(grep -Ev ^'[[:space:]]*(#|$)' requirements/requirements.txt | cat) && \
    pixi add --pypi $(grep -Ev ^'[[:space:]]*(#|$)' requirements/dev.txt | cat) && \
    pixi add --pypi $(grep -Ev ^'[[:space:]]*(#|$)' requirements/pandas.txt | cat) && \
    pixi add --pypi $(grep -Ev ^'[[:space:]]*(#|$)' requirements/polars.txt | cat) && \
    pixi add --pypi ipykernel jupyterlab notebook

COPY . .
RUN pip install .

RUN pixi shell-hook > /shell-hook.sh

# Create the shell-hook bash script to activate the environment
RUN pixi shell-hook -e prod > /shell-hook.sh

# extend the shell-hook script to run the command passed to the container
RUN echo 'exec "$@"' >> /shell-hook.sh

FROM --platform=${PLATFORM} gcr.io/distroless/base-debian12 AS production

WORKDIR /app

COPY --from=build /app /app
COPY --from=build /shell-hook.sh /shell-hook.sh

ENTRYPOINT [ "/bin/bash", "/shell-hook.sh" ]

CMD ["python"]
