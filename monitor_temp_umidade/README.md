# Monitor de Temperatura para Home Assistant

Este projeto implementa um sistema de monitoramento de temperatura usando o sensor interno do Raspberry Pi Pico W, que envia os dados para o Home Assistant via protocolo MQTT.

## Visão Geral

Este projeto utiliza o microcontrolador Raspberry Pi Pico W para ler a temperatura do seu sensor interno e publicar esses dados em um servidor MQTT, que pode ser integrado ao Home Assistant para visualização e automação.

O sistema realiza as seguintes operações:
- Conecta-se a uma rede Wi-Fi
- Estabelece conexão com um broker MQTT
- Lê periodicamente a temperatura do sensor interno do Pico W
- Publica as leituras no tópico MQTT configurado
- Fornece status de disponibilidade do dispositivo
- Reconecta-se automaticamente em caso de falhas

## Hardware Necessário

- Raspberry Pi Pico W
- Cabo micro-USB para alimentação e programação
- Computador para carregar o firmware

## Arquivos do Projeto

- `main.py`: Código principal que executa no Pico W
- `umqtt/simple.py`: Biblioteca MQTT para MicroPython
- `configuration.yaml`: Exemplo de configuração para o Home Assistant

## Configuração

### 1. Configuração Wi-Fi e MQTT

Antes de carregar o código, você precisa configurar as credenciais da sua rede Wi-Fi e do seu servidor MQTT. Edite as seguintes variáveis no arquivo `main.py`:

```python
# Configurações de Rede Wi-Fi
WIFI_SSID = "SEU_NOME_DE_REDE_WIFI"
WIFI_PASSWORD = "SUA_SENHA_WIFI"

# Configurações do Broker MQTT
MQTT_BROKER = "ENDERECO_DO_SEU_BROKER_MQTT"  # Ex: "192.168.1.100" ou "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_USER = "SEU_USUARIO_MQTT"  # Deixe em branco se não houver autenticação
MQTT_PASSWORD = "SUA_SENHA_MQTT" # Deixe em branco se não houver autenticação
```

### 2. Intervalos de Leitura

Para ajustar o intervalo de tempo entre as leituras de temperatura, modifique a variável:

```python
INTERVALO_LEITURA = 60  # Intervalo de leitura em segundos
```

### 3. Tópicos MQTT

Os tópicos MQTT padrão são:
- `bitdoglab/sensor/temperatura_interna`: Para os dados de temperatura
- `bitdoglab/status/temp_interna_sensor`: Para o status do dispositivo

## Instalação

1. Instale o firmware MicroPython no seu Raspberry Pi Pico W
2. Copie os arquivos `main.py` e a pasta `umqtt` para o dispositivo
3. Reinicie o Pico para que o código comece a ser executado

## Integração com Home Assistant

1. Adicione o conteúdo do arquivo `configuration.yaml` fornecido ao seu arquivo de configuração do Home Assistant
2. Reinicie o Home Assistant
3. O sensor de temperatura deve aparecer automaticamente no seu painel

## Estrutura dos Dados

Os dados são publicados no seguinte formato:
- Temperatura: valor numérico em graus Celsius
- Status: "online" quando o dispositivo está funcionando

## Resolução de Problemas

Se o sensor não aparecer no Home Assistant:
1. Verifique se o Pico W está conectado à rede Wi-Fi (mensagens de console)
2. Confirme se o broker MQTT está acessível e funcionando
3. Verifique se os tópicos MQTT no Home Assistant correspondem aos configurados no código.