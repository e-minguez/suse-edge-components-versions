FROM registry.suse.com/bci/python:3.12

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
		zypper install -y helm && \
		zypper clean --all

COPY suse-edge-components-versions.py edge-versions/ ./

ENTRYPOINT ["python3", "suse-edge-components-versions.py"]