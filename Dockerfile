FROM registry.suse.com/bci/python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
		zypper install -y helm && \
		zypper clean --all

COPY get_versions.py .

ENTRYPOINT ["python3", "get_versions.py"]