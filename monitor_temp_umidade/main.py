
import network
import time
from machine import ADC # Importa a classe ADC
from umqtt.simple import MQTTClient

# Configurações de Rede Wi-Fi
WIFI_SSID = "SEU_NOME_DE_REDE_WIFI"
WIFI_PASSWORD = "SUA_SENHA_WIFI"

# Configurações do Broker MQTT
MQTT_BROKER = "ENDERECO_DO_SEU_BROKER_MQTT"  # Ex: "192.168.1.100" ou "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_USER = "SEU_USUARIO_MQTT"  # Deixe em branco se não houver autenticação
MQTT_PASSWORD = "SUA_SENHA_MQTT" # Deixe em branco se não houver autenticação
MQTT_CLIENT_ID = "bitdoglab_sensor_temp_interna_pico"

# Tópicos MQTT
MQTT_TOPIC_TEMP = "bitdoglab/sensor/temperatura_interna"
MQTT_TOPIC_STATUS = "bitdoglab/status/temp_interna_sensor"

# Intervalo de leitura e publicação (em segundos)
INTERVALO_LEITURA = 60

# Inicialização do sensor de temperatura interno (ADC4)
# O ADC(4) é o canal para o sensor de temperatura interno do RP2040
sensor_temp_adc = ADC(4)

# Função para conectar ao Wi-Fi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Conectando à rede {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout_wifi = 0
        while not wlan.isconnected() and timeout_wifi < 20:
            print(".", end="")
            time.sleep(1)
            timeout_wifi += 1
        if wlan.isconnected():
            print(f"\nConectado! Endereço IP: {wlan.ifconfig()[0]}")
        else:
            print("\nFalha ao conectar ao Wi-Fi. Verifique as credenciais e a rede.")
            return None
    else:
        print(f"Já conectado à rede {WIFI_SSID}. IP: {wlan.ifconfig()[0]}")
    return wlan

# Função para conectar ao Broker MQTT
def connect_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD)
    try:
        client.connect()
        print(f"Conectado ao broker MQTT: {MQTT_BROKER}")
        client.publish(MQTT_TOPIC_STATUS, "online", retain=True)
        return client
    except Exception as e:
        print(f"Falha ao conectar ao broker MQTT: {e}")
        return None

# Função para ler e converter a temperatura do sensor interno
def read_internal_temp():
    try:
        adc_value = sensor_temp_adc.read_u16()
        # Fórmula de conversão fornecida na documentação do RP2040 / MicroPython
        # A tensão de referência é 3.3V. read_u16() retorna valor de 0-65535.
        voltage = adc_value * (3.3 / 65535)
        # Fórmula de conversão para temperatura em Celsius
        temperature = 27 - (voltage - 0.706) / 0.001721
        return temperature
    except Exception as e:
        print(f"Erro ao ler sensor de temperatura interno: {e}")
        return None

# Loop principal
def run():
    wlan = connect_wifi()
    if not wlan or not wlan.isconnected():
        print("Não foi possível conectar ao Wi-Fi. Reiniciando em 60 segundos...")
        time.sleep(60)
        machine.reset()
        return

    mqtt_client = connect_mqtt()
    if not mqtt_client:
        print("Não foi possível conectar ao MQTT. Reiniciando em 60 segundos...")
        time.sleep(60)
        machine.reset()
        return

    print("Monitoramento de temperatura interna iniciado...")
    last_read_time = 0
    while True:
        try:
            current_time = time.time()
            if (current_time - last_read_time) >= INTERVALO_LEITURA:
                temperatura = read_internal_temp()

                if temperatura is not None:
                    print(f"Temperatura Interna do Pico: {temperatura:.2f}°C")
                    mqtt_client.publish(MQTT_TOPIC_TEMP, str(round(temperatura, 2)))
                    print("Dado de temperatura interna publicado via MQTT.")
                else:
                    print("Falha ao ler temperatura interna.")
                    # Opcional: publicar um status de erro do sensor
                    # mqtt_client.publish(MQTT_TOPIC_STATUS, "error_reading_sensor", retain=True)
                
                last_read_time = current_time
            
            time.sleep(1)

        except OSError as e:
            print(f"Erro de comunicação MQTT: {e}")
            print("Tentando reconectar ao MQTT...")
            if mqtt_client: mqtt_client.disconnect()
            mqtt_client = connect_mqtt()
            if not mqtt_client:
                print("Falha ao reconectar ao MQTT. Reiniciando o dispositivo...")
                time.sleep(10)
                machine.reset()
            else:
                print("Reconectado ao MQTT com sucesso.")
                mqtt_client.publish(MQTT_TOPIC_STATUS, "online", retain=True)
        except Exception as e:
            print(f"Erro inesperado: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run()

