FROM lexiforest/curl-impersonate:alpine

RUN apk add --no-cache python3 py3-pip
RUN pip3 install flask --break-system-packages

WORKDIR /app
COPY app.py .

EXPOSE 5555

CMD ["python3", "app.py"]
