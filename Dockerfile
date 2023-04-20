FROM UBUNTU:22.04
RUN apt update && apt install -y nmap nano ssh tcdump iperf3 netcat net-tools traceroute iproute2 iputils-arping iputils-ping iputils-tracepath inetutils-telnet telnet-ssl telnet lynx python3 python3-pip

RUN ln -fs /usr/share/zoneinfo/Europe/paris /etc/localtime && apt-get install -y software-properties-common && add-apt-repository -y ppa:deadsnakes/ppa && apt-get update && apt-get install -y python3.9 git

RUN pip3 install sockets zeroconf thread6 argparse python-time netifaces