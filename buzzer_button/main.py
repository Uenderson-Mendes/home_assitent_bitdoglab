# main.py - Leitura de Botões e Controle de Buzzer da BitDogLab via MQTT

import network
import time
from machine import Pin, PWM
from umqtt.simple import MQTTClient
import json

# Informações do WiFi
WIFI_SSID = "SEU_NOME_DE_REDE_WIFI"
WIFI_PASSWORD = "SUA_SENHA_WIFI"

# Configurações do Broker MQTT
MQTT_BROKER = "ENDERECO_DO_SEU_BROKER_MQTT"  # Ex: "192.168.1.100" ou "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_USER = "SEU_USUARIO_MQTT"  # Deixe em branco se não houver autenticação
MQTT_PASSWORD = "SUA_SENHA_MQTT" # Deixe em branco se não houver autenticação
MQTT_CLIENT_ID = "bitdoglab_io_controller"

# Tópicos MQTT
MQTT_TOPIC_BUTTON_A_STATE = "bitdoglab/button/a/state"
MQTT_TOPIC_BUTTON_B_STATE = "bitdoglab/button/b/state"
MQTT_TOPIC_BUTTON_C_STATE = "bitdoglab/button/c/state"
MQTT_TOPIC_BUZZER_COMMAND = "bitdoglab/buzzer/command" # Receber comandos para o buzzer
MQTT_TOPIC_BUZZER_STATE = "bitdoglab/buzzer/state"   # Publicar estado do buzzer (ON/OFF)
MQTT_TOPIC_STATUS = "bitdoglab/io/status"

# Pinos dos Botões e Buzzer
PIN_BUTTON_A = 10
PIN_BUTTON_B = 5
PIN_BUTTON_C = 6
PIN_BUZZER = 21

# Configuração dos Pinos dos Botões com Pull-up interno e Interrupção
# Estado inicial: HIGH (não pressionado), LOW (pressionado)
button_a = Pin(PIN_BUTTON_A, Pin.IN, Pin.PULL_UP)
button_b = Pin(PIN_BUTTON_B, Pin.IN, Pin.PULL_UP)
button_c = Pin(PIN_BUTTON_C, Pin.IN, Pin.PULL_UP)

# Configuração do PWM para o Buzzer
buzzer_pwm = PWM(Pin(PIN_BUZZER))
buzzer_pwm.duty_u16(0) # Buzzer desligado inicialmente
buzzer_state = "OFF"

# Debounce para botões (evitar múltiplas detecções por um único pressionamento)
last_press_time = {"A": 0, "B": 0, "C": 0}
DEBOUNCE_MS = 200 # 200 milissegundos

# Cliente MQTT (declarado globalmente para ser acessível nas interrupções)
client = None

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
            print("\nFalha ao conectar ao Wi-Fi.")
            return None
    else:
        print(f"Já conectado à rede {WIFI_SSID}. IP: {wlan.ifconfig()[0]}")
    return wlan

# Handler de interrupção para os botões
def button_handler(pin):
    global client, last_press_time
    button_id = ""
    topic = ""
    current_time = time.ticks_ms()

    if pin == button_a:
        button_id = "A"
        topic = MQTT_TOPIC_BUTTON_A_STATE
    elif pin == button_b:
        button_id = "B"
        topic = MQTT_TOPIC_BUTTON_B_STATE
    elif pin == button_c:
        button_id = "C"
        topic = MQTT_TOPIC_BUTTON_C_STATE
    else:
        return

    # Debounce: ignora se o último pressionamento foi muito recente
    if time.ticks_diff(current_time, last_press_time[button_id]) < DEBOUNCE_MS:
        return
    last_press_time[button_id] = current_time

    # O valor do pino é 0 (LOW) quando pressionado (devido ao PULL_UP)
    state_payload = "ON" if pin.value() == 0 else "OFF"
    print(f"Botão {button_id} Pressionado. Estado: {pin.value()} -> Payload: {state_payload}")
    
    if client and topic:
        try:
            client.publish(topic, state_payload, retain=False) # Botões são eventos, retain=False é comum
            # Para Home Assistant, é melhor enviar ON e OFF separados.
            # Se pressionado (pin.value() == 0), envia ON.
            # O Home Assistant pode precisar de uma automação para resetar para OFF ou usar `off_delay`.
            # Alternativamente, o Pico pode enviar OFF após um tempo, ou na liberação do botão.
            # Para este exemplo, vamos enviar ON ao pressionar e OFF ao liberar (se a interrupção pegar os dois flancos)
            # A configuração IRQ_FALLING | IRQ_RISING faz isso.
        except Exception as e:
            print(f"Erro ao publicar estado do botão {button_id}: {e}")

# Configura as interrupções para os botões (detecta tanto ao pressionar quanto ao soltar)
button_a.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button_handler)
button_b.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button_handler)
button_c.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=button_handler)

# Função para controlar o buzzer
def control_buzzer(command):
    global buzzer_pwm, buzzer_state, client
    # Exemplo de comando: {"state": "ON", "frequency": 1000, "duration": 0.5} ou {"state": "OFF"}
    try:
        if isinstance(command, bytes): command = command.decode()
        if isinstance(command, str): command = json.loads(command)
        
        if "state" in command:
            if command["state"].upper() == "ON":
                freq = command.get("frequency", 1000) # Frequência em Hz
                duty = command.get("duty", 32768)    # 50% duty cycle (0-65535)
                duration = command.get("duration", 0) # Duração em segundos (0 para contínuo até OFF)
                
                buzzer_pwm.freq(freq)
                buzzer_pwm.duty_u16(duty)
                buzzer_state = "ON"
                print(f"Buzzer ON: Freq={freq}Hz, Duty={duty}, Duração={duration}s")
                
                if duration > 0:
                    time.sleep(duration)
                    buzzer_pwm.duty_u16(0) # Desliga após a duração
                    buzzer_state = "OFF"
                    print("Buzzer OFF (automático após duração)")
            
            elif command["state"].upper() == "OFF":
                buzzer_pwm.duty_u16(0)
                buzzer_state = "OFF"
                print("Buzzer OFF (comando)")
        
        if client:
            client.publish(MQTT_TOPIC_BUZZER_STATE, buzzer_state, retain=True)
            
    except Exception as e:
        print(f"Erro ao controlar buzzer: {e}")
        buzzer_pwm.duty_u16(0) # Garante que o buzzer desligue em caso de erro
        buzzer_state = "OFF"
        if client: client.publish(MQTT_TOPIC_BUZZER_STATE, buzzer_state, retain=True)

# Callback para mensagens MQTT (para o buzzer)
def mqtt_callback(topic, msg, retained=False, dup=False):
    print(f"Comando MQTT recebido - Tópico: {topic.decode()}, Mensagem: {msg.decode()}")
    if topic.decode() == MQTT_TOPIC_BUZZER_COMMAND:
        control_buzzer(msg)

# Função para conectar ao Broker MQTT
def connect_mqtt():
    global client
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD)
    client.set_callback(mqtt_callback)
    try:
        client.connect()
        print(f"Conectado ao broker MQTT: {MQTT_BROKER}")
        client.subscribe(MQTT_TOPIC_BUZZER_COMMAND)
        print(f"Inscrito no tópico de comando do buzzer: {MQTT_TOPIC_BUZZER_COMMAND}")
        client.publish(MQTT_TOPIC_STATUS, "online", retain=True)
        client.publish(MQTT_TOPIC_BUZZER_STATE, buzzer_state, retain=True) # Publica estado inicial
        # Publica estado inicial dos botões (OFF, pois não estão pressionados no início)
        client.publish(MQTT_TOPIC_BUTTON_A_STATE, "OFF", retain=False)
        client.publish(MQTT_TOPIC_BUTTON_B_STATE, "OFF", retain=False)
        client.publish(MQTT_TOPIC_BUTTON_C_STATE, "OFF", retain=False)
        return client
    except Exception as e:
        print(f"Falha ao conectar ou inscrever no broker MQTT: {e}")
        return None

# Loop principal
def run():
    wlan = connect_wifi()
    if not wlan or not wlan.isconnected():
        print("Não foi possível conectar ao Wi-Fi. Reiniciando...")
        time.sleep(60)
        machine.reset()

    mqtt_client = connect_mqtt()
    if not mqtt_client:
        print("Não foi possível conectar ao MQTT. Reiniciando...")
        time.sleep(60)
        machine.reset()

    print("Aguardando interações (botões) e comandos MQTT (buzzer)...")
    while True:
        try:
            mqtt_client.check_msg() # Processa mensagens MQTT para o buzzer
            time.sleep(0.1) # Pequena pausa
        except OSError as e:
            print(f"Erro de comunicação MQTT: {e}. Tentando reconectar...")
            time.sleep(5)
            if mqtt_client: mqtt_client.disconnect()
            mqtt_client = connect_mqtt()
            if not mqtt_client:
                print("Falha grave ao reconectar MQTT. Reiniciando dispositivo...")
                time.sleep(10)
                machine.reset()
            else:
                print("Reconectado ao MQTT com sucesso.")
                client.publish(MQTT_TOPIC_STATUS, "online", retain=True)
                client.publish(MQTT_TOPIC_BUZZER_STATE, buzzer_state, retain=True)
        except Exception as e:
            print(f"Erro inesperado no loop principal: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run()

