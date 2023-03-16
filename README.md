# Sistema distribuído para Reconhecimento de Atividades em Casas Inteligentes

## Descrição

O objetivo principal desta investigação é desenvolver um sistema de deteção e classificação de padrões de atividades através da captura de imagens em tempo real que sejam relevantes para o contexto do utilizador, sempre mantendo a privacidade como um dos requisitos fundamentais.  

## Como utilizar?

### · NVIDIA® Jetson Nano™ 2GB Developer Kit
As instruções para instalar o software necessário num Jetson Nano encontram-se [INSTALL_JETSON_NANO_2GB](https://github.com/LuisMota1999/Distributed-Smart-Camera-AAL-System/blob/master/INSTALL_JETSON_NANO_2GB.md).

### · Home Assistant

Para mais informações consultar a [documentação](https://www.home-assistant.io/installation/linux#docker-compose) do Home Assistant.

1. Instalar e Testar o Docker:
   
    1.
            sudo apt-get update
            sudo apt-get install \
            ca-certificates \
            curl \
            gnupg \
            lsb-release
    2.      sudo mkdir -m 0755 -p /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    3.      sudo chmod a+r /etc/apt/keyrings/docker.gpg
            sudo apt-get update
    4.      sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            sudo docker run hello-world

2. Instalar o comando nano para editar ficheiros no terminal:
    
        sudo apt install nano
        cd /opt
        sudo nano docker-compose.yaml

3. Configurar ficheiro YAML (docker-compose.yaml):

        version: '3'
        services:
          portainer:
            image: portainer/portainer-ce:latest
            container_name: portainer
            restart: unless-stopped
            security_opt:
                - no-new-privileges:true
            volumes: 
                - /etc/localtime:/etc/localtime:ro
                - /var/run/docker.sock:/var/run/docker.sock:ro
                - ./portainer-data:/data
            ports:
                - 9000:9000
          homeassistant:
            container_name: homeassistant
            image: "ghcr.io/home-assistant/home-assistant:stable"
            volumes:
              - /opt/homeassistant/config:/config
              - /etc/localtime:/etc/localtime:ro
            restart: unless-stopped
            privileged: true
            network_mode: host

4. Iniciar o(s) serviço(s):

        docker compose up -d 

### Para Desenvolvedores

- Usar Python 3.9.
- Instalar todas as dependências necessárias no projeto
- Os datasets não estão incluídos no repositório GitHub por possuirem um tamanho bastante elevado.  Se o disco do projeto não for suficiente para guardar os datasets, o caminho para os mesmos, pode ser passado como argumento para os ficheiros de retreino.


## Autor

* Luís mota


<br>
<div align="center">
  <a href="https://github.com/LuisMota1999" style="text-decoration:none;">
    <img src="https://camo.githubusercontent.com/4133dc1cd4511d4a292b84ce10e52e4ed92569fb2a8165381c9c47be5edc2796/68747470733a2f2f6564656e742e6769746875622e696f2f537570657254696e7949636f6e732f696d616765732f706e672f6769746875622e706e67" width="5%" style=" border-radius:100%" alt="" /></a>
  <img src="https://github.com/ultralytics/assets/raw/main/social/logo-transparent.png" width="3%" alt="" />
  <a href="mailto: 38186@ufp.edu.pt" style="text-decoration:none;">
    <img src="https://camo.githubusercontent.com/0f3aa1f457bb92fbd2411761262ce1fb0f766ed74a4f4289bfc4a0b6024335d6/68747470733a2f2f6564656e742e6769746875622e696f2f537570657254696e7949636f6e732f696d616765732f7376672f656d61696c2e737667" width="5%" style=" border-radius:100%" alt="" /></a>
</div>

