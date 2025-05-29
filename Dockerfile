FROM ubuntu:latest
LABEL authors="gustavo"

ENTRYPOINT ["top", "-b"]