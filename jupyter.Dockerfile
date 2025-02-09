ARG PLATFORM=linux/amd64
ARG NONROOT_UID=65532

# Stage 1: Build your Python application
FROM --platform=${PLATFORM} ghcr.io/astral-sh/uv:python3.13-bookworm AS build
WORKDIR /app
ENV UV_LINK_MODE=copy
ARG NONROOT_UID
COPY . .
RUN adduser --disabled-password --home /home/nonroot --uid ${NONROOT_UID} --gecos "" nonroot && \
    chown -R nonroot:nonroot /app && \
    chown -R nonroot:nonroot /home/nonroot && \
    uv python pin 3.13
USER nonroot
RUN --mount=type=cache,target=/home/nonroot/.cache/uv,uid=$NONROOT_UID,gid=$NONROOT_UID \
    uv venv && \
    uv sync && \
    uv pip install ipykernel jupyterlab notebook

# Stage 2: Final production stage using distroless
FROM --platform=${PLATFORM} gcr.io/distroless/base-debian12:debug-nonroot AS production
WORKDIR /app

# Copy in the shared libraries from the build stage.
COPY --from=build /usr/local/lib/ /usr/local/lib/
COPY --from=build /lib/x86_64-linux-gnu /lib/x86_64-linux-gnu
COPY --from=build /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu

# Ensure the runtime finds these libraries.
ENV LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu"
ENV PATH="/app/.venv/bin:${PATH}"

# Copy the Python executables and application files from the build stage.
COPY --from=build /lib/terminfo /lib/terminfo
COPY --from=build /usr/local/bin/python* \
    /usr/local/bin/ncurses* /usr/local/bin/sqlite3* /usr/local/bin/openssl* /usr/local/bin/
COPY --from=build /app /app

ENTRYPOINT [ "/app/.venv/bin/python" ]
CMD ["/app/.venv/bin/jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser"]
