FROM ubuntu:22.04
RUN apt update && apt install -y nmap nano ssh tcpdump iperf3 netcat net-tools traceroute iproute2 iputils-arping iputils-ping iputils-tracepath inetutils-telnet telnet-ssl telnet lynx python3 python3-pip

RUN ln -fs /usr/share/zoneinfo/Europe/Brussels /etc/localtime && apt-get install -y software-properties-common && add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && apt-get install -y python3.9 git openssh-client

ARG GITHUB_TOKEN
# Configure SSH and Git with the token
RUN mkdir -p /root/.ssh && \
    echo "StrictHostKeyChecking no" > /root/.ssh/config && \
    ssh-keyscan github.com >> /root/.ssh/known_hosts && \
    git config --global credential.helper store && \
    echo "https://$GITHUB_TOKEN:x-oauth-basic@github.com" > /root/.git-credentials

# Clone the private GitHub repository
RUN git clone https://github.com/LuisMota1999/Distributed-Smart-Camera-AAL-System/ /app
WORKDIR /app

RUN pip3 install sockets zeroconf thread6 argparse python-time netifaces sphinx flask requests pyOpenSSL

