# rele_mqtt_botao_b.py - Controle de Relé com Botão B e MQTT na BitDogLab

from machine import Pin
from umqtt.simple import MQTTClient
import network
import time
import json # Embora não estritamente necessário para comandos ON/OFF simples, pode ser útil para estados futuros

# --- Configurações do Usuário ---
WIFI_SSID = "SEU_NOME_DE_REDE_WIFI"
WIFI_PASSWORD = "SUA_SENHA_WIFI"

# Configurações do Broker MQTT
MQTT_BROKER = "ENDERECO_DO_SEU_BROKER_MQTT"  # Ex: "192.168.1.100" ou "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_USER = "SEU_USUARIO_MQTT"  # Deixe em branco se não houver autenticação
MQTT_PASSWORD = "SUA_SENHA_MQTT" # Deixe em branco se não houver autenticação
MQTT_CLIENT_ID = "bitdoglab_sensor_temp_interna_pico"
MQTT_CLIENT_ID = "bitdoglab_rele_controller_b"

# Pinos (conforme informado pelo usuário)
PIN_BUTTON_B = 5
PIN_RELE = 20

# Tópicos MQTT
MQTT_TOPIC_RELE_STATE = "bitdoglab/rele/gpio20/state"    # Publica o estado atual (ON/OFF)
MQTT_TOPIC_RELE_COMMAND = "bitdoglab/rele/gpio20/set"  # Recebe comandos (ON/OFF)
MQTT_TOPIC_RELE_AVAILABILITY = "bitdoglab/rele/gpio20/status"
# --- Fim das Configurações do Usuário ---

# Configuração dos Pinos
button_b = Pin(PIN_BUTTON_B, Pin.IN, Pin.PULL_UP)
rele = Pin(PIN_RELE, Pin.OUT)

# Estado inicial e variáveis de controle
rele_estado_atual = 0  # 0 para OFF, 1 para ON
rele.value(rele_estado_atual)

last_button_press_time = 0
DEBOUNCE_MS = 250 # Aumentado um pouco para botões físicos

mqtt_client = None

def set_rele_state(novo_estado, origem="script"):
    global rele_estado_atual, mqtt_client
    rele_estado_atual = novo_estado
    rele.value(rele_estado_atual)
    estado_str = "ON" if rele_estado_atual == 1 else "OFF"
    print(f"Relé {estado_str} (Origem: {origem})")
    if mqtt_client:
        try:
            mqtt_client.publish(MQTT_TOPIC_RELE_STATE, estado_str.encode(), retain=True)
        except Exception as e:
            print(f"Erro ao publicar estado do relé: {e}")

def toggle_rele_local():
    novo_estado = 1 - rele_estado_atual
    set_rele_state(novo_estado, origem="botao_local")

def mqtt_callback(topic, msg, *args):
    global rele_estado_atual
    print(f"Mensagem recebida - Tópico: {topic.decode()}, Mensagem: {msg.decode()}")
    comando = msg.decode().upper()
    
    if topic.decode() == MQTT_TOPIC_RELE_COMMAND:
        if comando == "ON" and rele_estado_atual == 0:
            set_rele_state(1, origem="mqtt")
        elif comando == "OFF" and rele_estado_atual == 1:
            set_rele_state(0, origem="mqtt")
        elif comando == "TOGGLE":
             novo_estado = 1 - rele_estado_atual
             set_rele_state(novo_estado, origem="mqtt_toggle")
        else:
            print(f"Comando MQTT inválido ou estado já é {comando}")
    else:
        print(f"Mensagem recebida em tópico inesperado: {topic.decode()}")

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
            print(f"\nConectado ao Wi-Fi! IP: {wlan.ifconfig()[0]}")
            return True
        else:
            print("\nFalha ao conectar ao Wi-Fi.")
            return False
    print(f"Já conectado ao Wi-Fi. IP: {wlan.ifconfig()[0]}")
    return True

def connect_and_subscribe_mqtt():
    global mqtt_client
    mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD)
    mqtt_client.set_callback(mqtt_callback)
    try:
        mqtt_client.connect()
        print(f"Conectado ao broker MQTT: {MQTT_BROKER}")
        mqtt_client.subscribe(MQTT_TOPIC_RELE_COMMAND)
        print(f"Inscrito no tópico de comando: {MQTT_TOPIC_RELE_COMMAND}")
        # Publica disponibilidade e estado inicial
        mqtt_client.publish(MQTT_TOPIC_RELE_AVAILABILITY, b"online", retain=True)
        initial_state_str = "ON" if rele_estado_atual == 1 else "OFF"
        mqtt_client.publish(MQTT_TOPIC_RELE_STATE, initial_state_str.encode(), retain=True)
        return True
    except OSError as e:
        print(f"Falha ao conectar ao broker MQTT: {e}")
        return False
    except Exception as e:
        print(f"Outro erro MQTT: {e}")
        return False

print("Iniciando controle de relé com Botão B e MQTT...")
print(f"Botão B (GPIO{PIN_BUTTON_B}), Relé (GPIO{PIN_RELE})")

if not connect_wifi():
    print("Não foi possível conectar ao Wi-Fi. Verifique as configurações e reinicie.")
    # Poderia tentar um soft reset ou entrar em modo de espera
else:
    if not connect_and_subscribe_mqtt():
        print("Não foi possível conectar ao MQTT. Verifique as configurações e reinicie.")
        # Poderia tentar um soft reset ou entrar em modo de espera
    else:
        print("Sistema pronto. Pressione o Botão B ou envie comandos MQTT.")

        while True:
            try:
                # Verifica botão B
                if button_b.value() == 0: # Botão pressionado (LOW)
                    current_time = time.ticks_ms()
                    if time.ticks_diff(current_time, last_button_press_time) > DEBOUNCE_MS:
                        last_button_press_time = current_time
                        toggle_rele_local()
                        # Pequena pausa para o usuário soltar o botão antes da próxima checagem
                        # e para evitar que o check_msg() seja chamado muitas vezes seguidas
                        # enquanto o botão está pressionado.
                        time.sleep_ms(DEBOUNCE_MS) 
                
                # Verifica mensagens MQTT
                if mqtt_client:
                    mqtt_client.check_msg()
                
                time.sleep_ms(20) # Pequena pausa no loop

            except OSError as e:
                print(f"Erro de OSError no loop principal: {e}")
                print("Tentando reconectar ao MQTT...")
                time.sleep(5)
                if mqtt_client: 
                    try:
                        mqtt_client.disconnect() # Tenta desconectar antes de reconectar
                    except: pass # Ignora erros na desconexão
                if not connect_and_subscribe_mqtt():
                    print("Falha ao reconectar ao MQTT. Reiniciando em 30s...")
                    time.sleep(30)
                    # machine.reset() # Descomente para reiniciar em caso de falha persistente
                else:
                    print("Reconectado ao MQTT com sucesso.")
            except Exception as e:
                print(f"Erro inesperado no loop principal: {e}")
                time.sleep(10)
                # machine.reset() # Descomente para reiniciar em caso de erro grave

