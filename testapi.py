import requests

url = "http://localhost:8000/api/analyze-error/"
data = {"error_description": "你的错题描述"}

with requests.post(url, data=data, stream=True) as r:
    for line in r.iter_lines():
        if line:
            print(line.decode('utf-8'))