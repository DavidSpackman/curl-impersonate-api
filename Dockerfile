FROM lexiforest/curl-impersonate:alpine

RUN apk add --no-cache python3 py3-pip

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt

COPY app.py .

EXPOSE 5555

CMD ["python3", "app.py"]
