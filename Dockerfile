FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

RUN echo "Europe/Madrid" > /etc/timezone
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/3bf863cc.pub
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu2004/x86_64/7fa2af80.pub

RUN apt-get update -q --fix-missing && \
    apt-get -y upgrade

RUN DEBIAN_FRONTEND=noninteractive apt-get -y install \
                        python3.10-venv \
			python3-pip \
                        autossh \
                        gcc

RUN DEBIAN_FRONTEND=noninteractive apt-get -y install \
                        redis \
                        virtualenv \
                        curl \
                        libreoffice \
                        libxml2-utils \
                        tzdata \
                        cmake \
                        git \
                        build-essential \
                        pkg-config \
                        libgoogle-perftools-dev && \
    apt-get autoremove -y && \
    apt-get autoclean

RUN DEBIAN_FRONTEND=noninteractive apt-get -y install nano

RUN curl -sL https://deb.nodesource.com/setup_20.x | bash - && \
        apt-get install -y nodejs && curl -L https://npmjs.org/install.sh | sh

# Create needed folders and virtual environment
RUN mkdir -p /opt/mutnmt
RUN mkdir /opt/mutnmt/scripts
COPY scripts/ /opt/mutnmt/scripts/
RUN python3.10 -m venv /opt/mutnmt/venv

# Upgrade and install needed pip build tools
RUN /usr/bin/bash -c "source /opt/mutnmt/venv/bin/activate && \
	pip install -U pip && \
	pip install setuptools wheel && \
        deactivate"

# Install python requirements
RUN /usr/bin/bash -c "source /opt/mutnmt/venv/bin/activate && \
	pip install -r /opt/mutnmt/scripts/requirements.txt && \
	deactivate"

# Install joeynmt through pip, delete this when removing joeynmt from project
RUN /usr/bin/bash -c "source /opt/mutnmt/venv/bin/activate && \   
	pip install joeynmt && \
	deactivate"

# Copy rest of application code
COPY . /opt/mutnmt/

# Run entry scripts
RUN /opt/mutnmt/scripts/install.sh
RUN /opt/mutnmt/scripts/minify.sh
CMD ./opt/mutnmt/scripts/docker-entrypoint.sh
