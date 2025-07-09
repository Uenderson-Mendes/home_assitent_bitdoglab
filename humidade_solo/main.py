from machine import Pin
import time
from umqtt.simple import MQTTClient
import network
import json

# --- Configurações WiFi ---
WIFI_SSID = "rede"
WIFI_PASSWORD = "internet"

# --- Configurações MQTT ---
MQTT_BROKER = "Seu IP ou URL do Broker MQTT"
MQTT_PORT = 1883
MQTT_USER = "seu_usuario_mqtt"
MQTT_PASSWORD = "sua_senha_mqtt"
MQTT_CLIENT_ID = "sensor_umidade_solo"
MQTT_TOPIC = "homeassistant/binary_sensor/umidade_solo/state"
MQTT_CONFIG_TOPIC = "homeassistant/binary_sensor/umidade_solo/config"

# --- Pinos ---
sensor_umidade_digital = Pin(8, Pin.IN, Pin.PULL_UP)  # Sensor
rele = Pin(20, Pin.OUT)  # Relé no GPIO 20

# Define o estado de solo úmido
LIMIAR_DIGITAL_UMIDO = 0

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando ao WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 0
        while not wlan.isconnected() and timeout < 10:
            print(".", end="")
            time.sleep(1)
            timeout += 1
        if not wlan.isconnected():
            print("\n❌ Falha ao conectar ao WiFi.")
            return False
    print("\n✅ Conectado ao WiFi:", wlan.ifconfig()[0])
    return True

def conectar_mqtt():
    global mqtt_client
    try:
        mqtt_client = MQTTClient(
            MQTT_CLIENT_ID, MQTT_BROKER,
            port=MQTT_PORT,
            user=MQTT_USER,
            password=MQTT_PASSWORD,
            keepalive=30
        )
        mqtt_client.connect()
        print("✅ Conectado ao MQTT")

        config = {
            "name": "Umidade do Solo",
            "device_class": "moisture",
            "state_topic": MQTT_TOPIC,
            "payload_on": "0",
            "payload_off": "1",
            "unique_id": "umidade_solo_digital",
            "device": {
                "identifiers": ["umidade_solo_digital"],
                "name": "Sensor de Umidade Digital",
                "model": "FC-28",
                "manufacturer": "BitDogLab"
            }
        }

        mqtt_client.publish(MQTT_CONFIG_TOPIC, json.dumps(config), retain=True)
        return mqtt_client
    except Exception as e:
        print(f"❌ Falha ao conectar ao MQTT: {e}")
        return None

print("--- Sistema Digital de Umidade do Solo ---")
if not conectar_wifi():
    print("Reiniciando em 5s...")
    time.sleep(5)
    import machine
    machine.reset()

mqtt_client = None
ultimo_estado_digital = None

while True:
    try:
        estado_digital = sensor_umidade_digital.value()
        print("\n--- Leitura Digital (GPIO8) ---")
        print(f"  Estado Bruto Digital: {estado_digital}")

        if estado_digital == LIMIAR_DIGITAL_UMIDO:
            print("  💧 Solo: ÚMIDO")
            rele.value(0)  # Desliga o relé
            print("  🔌 Relé DESLIGADO (sem irrigação)")
        else:
            print("  🔥 Solo: SECO")
            rele.value(1)  # Liga o relé
            print("  🔌 Relé LIGADO (irrigação ativa)")

        if estado_digital != ultimo_estado_digital:
            payload = b"1" if estado_digital == 1 else b"0"
            try:
                if mqtt_client is None:
                    mqtt_client = conectar_mqtt()
                if mqtt_client:
                    print(f"📡 Publicando no tópico {MQTT_TOPIC} -> {payload}")
                    mqtt_client.publish(MQTT_TOPIC, payload)
                    ultimo_estado_digital = estado_digital
                else:
                    print("⚠️ Falha na conexão MQTT.")
            except Exception as e_pub:
                print(f"❌ Erro ao publicar no MQTT: {e_pub}")
                try:
                    if mqtt_client:
                        mqtt_client.disconnect()
                        print("MQTT desconectado para reconexão.")
                except Exception as e_disc:
                    print(f"Erro ao desconectar MQTT: {e_disc}")
                mqtt_client = None
                time.sleep(2)
        else:
            print("  ⚠️ Nenhuma alteração. MQTT não enviado.")

        print("-" * 30)
        time.sleep(3)

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        try:
            if mqtt_client:
                mqtt_client.disconnect()
                print("MQTT desconectado.")
        except Exception as e_disc:
            print(f"Erro ao desconectar: {e_disc}")
        mqtt_client = None
        time.sleep(5)
