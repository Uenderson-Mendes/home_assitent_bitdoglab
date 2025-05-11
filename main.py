import network
import time
from machine import Pin
import ujson
from umqtt.simple import MQTTClient

# Informações do WiFi
WIFI_SSID = "SEU_WIFI"
WIFI_PASSWORD = "SUA_SENHA_WIFI"

# Informações do Servidor MQTT
MQTT_SERVER = "SEU_IP_DO_HOME_ASSISNTENT"  # Substitua pelo IP real
MQTT_PORT = 1883
MQTT_USER = "SEU_USUARIO_MQTT"
MQTT_PASS = "SUA_SENHA_MQTT"
MQTT_CLIENT_ID = "picow"

# Definição de tópicos MQTT
MQTT_TOPIC_STATE = "picow/interruptor1/state"
MQTT_TOPIC_CONFIG = "homeassistant/binary_sensor/picow/interruptor1/config"
# Novos tópicos para o LED
MQTT_TOPIC_LED_STATE = "picow/led1/state"
MQTT_TOPIC_LED_SET = "picow/led1/set"
MQTT_TOPIC_LED_CONFIG = "homeassistant/light/picow/led1/config"

# Variáveis
ultimo_valor = 0
time_counter = 0
estado_interruptor = False  # Estado lógico do interruptor (ligado/desligado)

# Pinos
PIN_BOTAO = 5
PIN_LED_EXTERNO = 13  # Pino para o LED externo
led = Pin("LED", Pin.OUT)  # LED onboard do Pico W
led_externo = Pin(PIN_LED_EXTERNO, Pin.OUT)  # LED externo controlável

# Intervalo de tempo para atualização periódica (em ms)
UPDATE_INTERVAL = 500
HEARTBEAT_INTERVAL = 600  # equivalente a 600 ciclos de 500ms = 5 minutos

# Configuração do botão
button = Pin(PIN_BOTAO, Pin.IN, Pin.PULL_UP)

# Instância do client MQTT
mqtt_client = None

def conectar_wifi():
    """Conecta ao WiFi"""
    print("Conectando ao WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Pisca o LED durante a conexão
    led.value(1)
    
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    # Aguarda conexão ou falha
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print("Aguardando conexão...")
        time.sleep(1)
    
    # Verifica status da conexão
    if wlan.status() != 3:
        led.value(0)
        print("Falha na conexão. Status:", wlan.status())
        return False
    
    # Conexão bem-sucedida
    print("Conectado ao WiFi!")
    status = wlan.ifconfig()
    print("IP:", status[0])
    led.value(0)
    return True

def mqtt_callback(topic, msg):
    """Callback para mensagens MQTT recebidas"""
    topic = topic.decode('utf-8')
    msg = msg.decode('utf-8')
    print(f"Mensagem recebida no tópico {topic}: {msg}")
    
    # Verificar se é comando para o LED
    if topic == MQTT_TOPIC_LED_SET:
        if msg == "ON":
            led_externo.value(1)
            publicar_mqtt(MQTT_TOPIC_LED_STATE, b"ON")
            print("LED externo ligado")
        elif msg == "OFF":
            led_externo.value(0)
            publicar_mqtt(MQTT_TOPIC_LED_STATE, b"OFF")
            print("LED externo desligado")

def iniciar_mqtt():
    """Inicializa a conexão MQTT"""
    global mqtt_client
    print("Iniciando MQTT...")
    
    try:
        mqtt_client = MQTTClient(
            MQTT_CLIENT_ID, 
            MQTT_SERVER,
            port=MQTT_PORT,
            user=MQTT_USER, 
            password=MQTT_PASS,
            keepalive=60
        )
        mqtt_client.set_callback(mqtt_callback)
        mqtt_client.connect()
        
        # Inscrever-se no tópico de controle do LED
        mqtt_client.subscribe(MQTT_TOPIC_LED_SET)
        
        print("MQTT conectado")
        return True
    except Exception as e:
        print("Falha ao conectar ao MQTT:", e)
        return False

def publicar_mqtt(topic, payload):
    """Publica mensagem MQTT"""
    try:
        mqtt_client.publish(topic, payload)
        print(f"Publicado no tópico {topic}: {payload}")
        return True
    except Exception as e:
        print("Erro ao publicar:", e)
        try:
            # Tenta reconectar
            mqtt_client.connect()
            # Inscrever-se novamente após reconexão
            mqtt_client.subscribe(MQTT_TOPIC_LED_SET)
            mqtt_client.publish(topic, payload)
            print("Reconectado e publicado com sucesso")
            return True
        except:
            print("Falha na reconexão MQTT")
            return False

def configurar_ha_discovery():
    """Configura discovery do Home Assistant"""
    # Configuração para o sensor (interruptor)
    config_sensor = {
        "expire_after": "600",
        "icon": "mdi:gesture-tap-button",
        "name": "Interruptor 1 Pico W",
        "state_topic": "picow/interruptor1/state"
    }
    publicar_mqtt(MQTT_TOPIC_CONFIG, ujson.dumps(config_sensor))
    
    # Configuração para o LED controlável
    config_led = {
        "name": "LED 1 Pico W",
        "unique_id": "picow_led1",
        "schema": "json",
        "state_topic": MQTT_TOPIC_LED_STATE,
        "command_topic": MQTT_TOPIC_LED_SET,
        "icon": "mdi:led-on",
        "optimistic": False
    }
    publicar_mqtt(MQTT_TOPIC_LED_CONFIG, ujson.dumps(config_led))

# Programa principal
print("Iniciando...")

# Conecta ao WiFi
if not conectar_wifi():
    print("Reinicie o dispositivo para tentar novamente")
else:
    # Inicializa MQTT
    if iniciar_mqtt():
        # Configura sensor no Home Assistant
        configurar_ha_discovery()
        
        # Primeira leitura
        leitura_botao = not button.value()  # Invertido devido ao pull-up
        print("Primeira Leitura:", leitura_botao)
        
        # Inicializa o estado do interruptor como desligado por padrão
        estado_interruptor = False
        ultimo_valor = leitura_botao
        publicar_mqtt(MQTT_TOPIC_STATE, b"OFF")
        
        # Envia estado inicial do LED
        led_externo.value(False)  # Inicia com o LED desligado
        publicar_mqtt(MQTT_TOPIC_LED_STATE, b"OFF")
        
        # Loop principal
        while True:
            # Verifica mensagens MQTT pendentes
            mqtt_client.check_msg()
            
            # Lê o estado do botão
            leitura_botao = not button.value()  # Invertido devido ao pull-up
            print("Leitura:", leitura_botao)
            
            # Acende o LED interno quando o botão é pressionado (para debug)
            led.value(leitura_botao)
            
            # Detecta borda de descida (quando o botão é solto)
            if leitura_botao != ultimo_valor:
                if leitura_botao == 1:  # Botão pressionado
                    ultimo_valor = leitura_botao
                    # Não faz nada aqui, apenas registra o pressionamento
                elif leitura_botao == 0 and ultimo_valor == 1:  # Botão solto após ser pressionado
                    ultimo_valor = leitura_botao
                    # Toggle do estado do interruptor quando o botão é solto
                    estado_interruptor = not estado_interruptor
                    
                    # Publica o novo estado
                    if estado_interruptor:
                        publicar_mqtt(MQTT_TOPIC_STATE, b"ON")
                    else:
                        publicar_mqtt(MQTT_TOPIC_STATE, b"OFF")
                    
                    # Opcional: toggle LED quando o estado muda
                    led_externo.value(estado_interruptor)
                    publicar_mqtt(MQTT_TOPIC_LED_STATE, b"ON" if led_externo.value() else b"OFF")
            
            # Contador para heartbeat periódico
            if time_counter < HEARTBEAT_INTERVAL:
                time_counter += 1
            else:
                # Enviar estado atual para manter o sensor ativo no HA
                publicar_mqtt(MQTT_TOPIC_STATE, b"ON" if estado_interruptor else b"OFF")
                
                # Enviar também o estado atual do LED
                publicar_mqtt(MQTT_TOPIC_LED_STATE, b"ON" if led_externo.value() else b"OFF")
                
                time_counter = 0
            
            time.sleep(UPDATE_INTERVAL / 1000)  # Converte ms para segundos