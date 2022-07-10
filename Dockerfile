# Example: docker build . -t dsvw && docker run -p 65412:65412 dsvw

FROM alpine:3.11

RUN apk --no-cache add git python3 py-lxml
    
RUN apk --no-cache add netcat-openbsd

RUN rm -rf /var/cache/apk/*

WORKDIR /
RUN git clone https://github.com/desandy/DSVM

WORKDIR /DSVM
RUN sed -i 's/127.0.0.1/0.0.0.0/g' dsvw.py

EXPOSE 65412

CMD ["python3", "dsvw.py"]
