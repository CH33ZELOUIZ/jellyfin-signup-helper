FROM python:3.12-slim
WORKDIR /app
COPY app.py apply-defaults.py ./
EXPOSE 8060
CMD ["python3", "app.py"]
