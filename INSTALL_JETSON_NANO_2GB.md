## Configurar Nvidia Jetson Nano 2GB 

### Pré-Requisitos:
- Nvidia Jetson Nano 2GB developer Kit (2)
- Camera (2)
- MicroSD UHS-I 64GB (2)
- Fonte de alimentação de 5v==3A do tipo USB-C (2)

##### 1. Instalar o sistema operativo num cartão.
Download de [Jetson Nano 2GB Image](https://developer.nvidia.com/jetson-nano-2gb-sd-card-image/) para instalar a imagem do Jetson Nano 2GB num cartão microSD. 

Para mais informações consultar: [Getting Started with Jetson Nano 2GB Developer Kit](https://developer.nvidia.com/embedded/learn/get-started-jetson-nano-2gb-devkit)

- <b>Via SDK Manager</b>

Através da versão 16.04, 18.04, 20.04 ou 22.04 de ubuntu é possível através SDK Manager da Nvidia realizar todo o processo de <i>flash</i> e boot inicial diretamente no Jetson Nano 2GB. Além disso, é necessário criar uma conta nvidia através do [site da nvidia](https://developer.nvidia.com/login) para ter o respetivo acesso. 

Para mais informações consultar [Nvidia SDK Manager Jetson Nano 2GB Documentation](https://docs.nvidia.com/sdk-manager/install-with-sdkm-jetson/index.html)

##### 2. Setup inicial.
Colocar o cartão microSD num dos Jetson Nano e fazer setup inicial, definindo o nome de utilizador e a senha de acesso.

##### 3. Depois de reboot, instalar updates adicionais
    sudo apt update  
    sudo apt upgrade

##### 4. Instalar packages necessárias
    sudo apt install python3-venv
    sudo apt install libportaudio2  
    sudo apt install libatlas-base-dev
    sudo apt install opencv-contrib-python

##### 5. Instalar as drivers do HAT
    git clone https://github.com/respeaker/seeed-voicecard.git  
    cd seeed-voicecard  
    sudo ./install.sh --compat-kernel  
    sudo reboot  
    arecord -L # Verificar se ficou bem instalado  

##### 6. Instalar o docker
    curl -fsSL https://get.docker.com -o get-docker.sh  
    sudo sh get-docker.sh

##### 7. Instalar e configurar Home Assistant (via Docker)
Seguir as configurações no [README.md](https://github.com/LuisMota1999/Distributed-Smart-Camera-AAL-System/blob/master/README.md) referentes ao Home Assistant.

##### 8. Testar a camera (Opcional)
    mkdir python-camera-example
    cd ./python-camera-example
    wget https://raw.githubusercontent.com/spatialaudio/python-sounddevice/0.4.1/examples/wire.py
    python3 -m venv ./venv
    source ./venv/bin/activate
    pip install sounddevice
    pip install numpy
    python3 wire.py # CTRL+C para terminar processo
    deactivate

##### 9. Testar o microfone (Opcional)
    mkdir python-audio-example
    cd ./python-audio-example
    wget https://raw.githubusercontent.com/spatialaudio/python-sounddevice/0.4.1/examples/wire.py
    python3 -m venv ./venv
    source ./venv/bin/activate
    pip install sounddevice
    pip install numpy
    python3 wire.py # CTRL+C para terminar processo
    deactivate

##### 10. Instalar Edge Device
    docker pull luis38186/distributed-aal-sys