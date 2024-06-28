import json
import socket
import time
import threading
import os
from kafka import KafkaProducer, KafkaConsumer
from Mapa import Mapa  # Ahora puedes importar Mapa
from Mapa2 import Mapa2  # Ahora puedes importar Mapa2
# Importar las clases necesarias para la autenticación de drones con criptografía
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import logging
from datetime import datetime
import uuid
import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError







# Direcciones y puertos
HOST = os.getenv('HOST_ENGINE')  # Usando 'engine' como valor predeterminado
PORT = int(os.getenv('PORT_ENGINE'))  # Usando 5555 como valor predeterminado
HOST_BROKER = os.getenv('HOST_BROKER')  # Usando 'kafka' como valor predeterminado
PORT_BROKER = int(os.getenv('PORT_BROKER'))  # Usando 19092 como valor predeterminado
CLIMATE_SERVICE_HOST = os.getenv('HOST_WEATHER')  # Usando 'weather' como valor predeterminado
CLIMATE_SERVICE_PORT = int(os.getenv('PORT_WEATHER'))  # Usando 4444 como valor predeterminado
PORT_ALIVE = int(os.getenv('PORT_ENGINE2'))
HOST_FRONT = os.getenv('HOST_FRONT')
PORT_FRONT = int(os.getenv('PORT_FRONT'))


# Constantes
TEMPERATURE_COMFORTABLE_LOW = 17
TEMPERATURE_COMFORTABLE_HIGH = 25
TEMPERATURE_COLD_LIMIT = 5
TEMPERATURE_HOT_LIMIT = 38  
END_SHOW_TOPIC = 'end_show'
FILENAME_DRONES = 'data/drones_registry.json'
CLAVE_AES = 'clave/claveCifrada.json'
FILENAME_FIGURAS= 'file/figures.json'
FILENAME_ACTUALIZACIONES = 'file/last_updates.json'

PUBLIC_KEY_PATH = '/app/public_key.pem'
PRIVATE_KEY_PATH = '/app/private_key.pem'
PUBLIC_KEYDRON_PATH = '/app/public_dron_keys.json'
AUDIT_LOGS_PATH = '/app/audit_logs'


#################################################
# Funciones para el Engine AUTHENTICATION
#################################################


class Engine:

    def __init__(self):
        self.confirmed_drones = set()
        self.mapa = Mapa()
        self.mapa2 = Mapa2()
        self.city = None
        self.weather = False
        #diccionario para guardar los drones bloqueados
        self.bloked_id_token = []
        # Configuración del logging para registrar en un archivo de auditoría
        # Generar un identificador único para esta instancia
        instance_id = uuid.uuid4()


        #LOGS PARA EL ENGINE
        self.logger = logging.getLogger('engine_logger')
        handler = logging.FileHandler(f'{AUDIT_LOGS_PATH}/audit_log_{instance_id}.txt')
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        #LOGS PARA Kafka
        self.kafka_logger = logging.getLogger('kafka_logger')
        kafka_handler = logging.FileHandler(f'{AUDIT_LOGS_PATH}/kafka_log_{instance_id}.txt')
        kafka_handler.setFormatter(logging.Formatter('%(message)s'))
        self.kafka_logger.addHandler(kafka_handler)
        self.kafka_logger.setLevel(logging.INFO)


       

    def restart(self):
        self.mapa = None
        self.mapa2 = None
        self.city = None
        self.weather = False
        print("Recursos liberados.")
    


    
    def update_map(self, message):
        # Extraer los datos del mensaje
        drone_id = message['ID_DRON']
        x = message['COORDENADA_X_ACTUAL']
        y = message['COORDENADA_Y_ACTUAL']
        color = message['COLOR']
        # Actualizar la posición en el mapa con los datos del dron
        self.mapa.update_position(x, y, drone_id, color)
        self.mapa2.update_position(x, y, drone_id, color)
        self.sendUpdatesOfDrones(message)



    def display_map(self):
        while self.weather == True: 
            #self.mapa.display()
            self.sendMap()
            time.sleep(1)
            print()
            
    
    def load_blocked_tokens(self):
        try:
            with open('FILENAME_BLOCKED_TOKENS', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []
    
    def load_drones(self):
        try:
            with open(FILENAME_DRONES, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []
    
        
    def wrap_coordinates(self, x, y):
        """Envuelve las coordenadas según la geometría esférica del mapa."""
        #Si la coordenada x es 0 se envuelve a la derecha
        # Si la coordenada x es 20 se envuelve a la izquierda
        # Si la coordenada y es 0 se envuelve hacia abajo
        # Si la coordenada y es 20 se envuelve hacia arriba
        if x == 0:
            x = self.mapa.size - 2
        elif x == self.mapa.size - 1:
            x = 1
        if y == 0:
            y = self.mapa.size - 2
        elif y == self.mapa.size - 1:
            y = 1
        return x, y
    

#################################ZONA DE AUTENTICACION DE DRONES#################################################
    def generate_keys(self):
        # Asegúrate de que los directorios existen
        os.makedirs(os.path.dirname(PUBLIC_KEY_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(PRIVATE_KEY_PATH), exist_ok=True)
        # Genera las claves si no existen
        if not os.path.exists(PRIVATE_KEY_PATH):
            # Genera una clave privada
            # Generar nuevas claves RSA (puede cambiar este bloque si ya tienes las claves)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Genera la clave pública desde la clave privada
            public_key = private_key.public_key()
            
            # Guarda la clave privada en un archivo
            pem = private_key.private_bytes(
                encoding= serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(PRIVATE_KEY_PATH, 'wb') as f:
                f.write(pem)
            # Guarda la clave pública en un archivo
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with open(PUBLIC_KEY_PATH, 'wb') as f:
                f.write(pem)
        
    def descifrarPrimerMensaje(self,data):
        # Leer la clave desde el archivo JSON
        try:
       
            with open(CLAVE_AES, 'r') as file:
                dataJson = json.load(file)
                clave = base64.b64decode(dataJson['clave'])
        except Exception as e:
            print("Error al cargar la clave.")
            print(f"Error: {e}")
        
        print("clave: ",clave)
        iv = data[8:24]  # Extraer el IV que está al inicio del mensaje cifrado
        mensaje = data  [24:]  # El mensaje cifrado es todo después del IV
        cipher = Cipher(algorithms.AES(clave), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        mensaje = decryptor.update(mensaje) + decryptor.finalize()
        print("Mensaje descifrado.",mensaje)

        self.engineMessagesToFront("Mensaje descifrado.")
        return mensaje 
    def autenticateOrSendPublicKey(self,data,conn,addr):
        #Si el mensaje esta encryptado con la clave publica del engine 
            try:
                # Comprobar si el mensaje comienza con el prefijo esperado para AES-CFB
                if data.startswith(b"AES-CFB:"):
                    data = self.descifrarPrimerMensaje(data)
                    data = json.loads((data).decode())
                else:
                    data = json.loads(data.decode())

                #Si el mensaje es "Obtener clave publica"
                if data['message'] == "Obtener clave publica":

                    self.engineMessagesToFront("Solicitud de clave pública recibida.")
                    self.enviar_clave_publica(conn, addr)
                    return True
                
            #Si mensaje esta encryptado con la clave publica del engine Capturar la excepcion y continuar
            except Exception as e:
                #registrar el evento de error
                self.registrar_evento("Error de autenticacion", f"Error: {e}")
                return False
                
    def handle_connection(self,conn, addr):
        print("Conectado por", addr)
        try:
            data = conn.recv(1024)
            boolAskForPublicKey = self.autenticateOrSendPublicKey(data,conn,addr)
            # Obtener la IP del dron desde la dirección de la conexión
            ip_dron = addr[0]
            # Registrar el evento de conexión  
            self.registrar_evento("Conexión recibida", f"Conexión desde {addr}", ip_origen=ip_dron)
       
            #Si el mensaje esta encryptado con la clave publica del engine
            if boolAskForPublicKey == False:
                #Desencriptar el mensaje con la clave privada del engine
                self.engineMessagesToFront("Desencriptando mensaje.")
                try:
                    with open('private_key.pem', 'rb') as file:
                        private_key = serialization.load_pem_private_key(
                            file.read(),
                            password=None,
                            backend=default_backend()
                        )
                except Exception as e:
                    self.engineMessagesToFront("Error al cargar la clave privada.")
                    self.registrar_evento("Error de carga de clave", f"Error: {e}")
                #Desencriptar el mensaje
                try:                 
                    decrypted_data = private_key.decrypt(
                        data,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                #Capturar excepcion si el mensaje no se puede desencriptar y imprimir el error
                except Exception as e:
                    if str(e) == "Ciphertext length must be equal to key size.":
                        self.guardarPublicKeys(data,self.bloked_id_token[-1]["id"])
                        return True
                    else:
                        self.registrar_evento("Error de desencriptación", f"Error: {e}")
                    
                #Obtener el mensaje en formato json
                self.engineMessagesToFront("Mensaje desencriptado.")
                data = json.loads(decrypted_data)
                self.registrar_evento("Mensaje recibido", f"Mensaje Desencriptado", ip_origen=ip_dron)

                #Convertir el mensaje a un diccionario de python para poder acceder a los datos y decodificarlos
                id_dron = data["id"]
                token = data["token"]
                self.autenticacionDron(conn,addr,id_dron,token)
                return True

        except Exception as e:
            self.registrar_evento("Error de conexión", f"Error: {e}")
    

    def guardarPublicKeys(self,data,id):
        #Guardar las claves publicas de los drones en un archivo
        try:
            #sino existe el archivo se crea
            os.makedirs(os.path.dirname(PUBLIC_KEYDRON_PATH), exist_ok=True)

            with open(PUBLIC_KEYDRON_PATH, 'r') as file:
                public_keys = json.load(file)
        #Si el archivo no existe crear un diccionario vacio
        except FileNotFoundError:
            public_keys = []
        #Guardar la clave publica del dron en un diccionario
        publicDronKey_base64 = base64.b64encode(data).decode('utf-8')
        public_keys.append({
            "id": id,
            "public_key": publicDronKey_base64
        })
        #Guardar el diccionario en el archivo
        with open(PUBLIC_KEYDRON_PATH, 'w') as file:
            json.dump(public_keys, file, indent=4)
        #Imprimir mensaje de que la clave publica del dron fue guardada exitosamente
        self.prueba_carga_clave(id)
        self.registrar_evento("Guardado de clave pública", f"Clave pública del dron {id} guardada exitosamente.")
        return True

    def prueba_carga_clave(self,id_esperado):
        with open(PUBLIC_KEYDRON_PATH, 'r') as file:
            public_keys = json.load(file)
        for key_info in public_keys:
            if key_info['id'] == id_esperado:
                try:
                    key = base64.b64decode(key_info['public_key'])
                    public_key = serialization.load_pem_public_key(key, backend=default_backend())
                except Exception as e:
                    self.registrar_evento("Error de carga de clave", f"Error cargando la clave: {e}")

    def autenticacionDron(self,conn,addr,id_dron,token):

        #Cargar los drones registrados
        drones_registered = self.load_drones()

        #Si el dron no esta registrado
        response = {"status": "error", "message": "Dron no autenticado"}

        #Si el dron esta bloqueado
        if self.bloked_id_token != []:
            self.engineMessagesToFront("verificando si el dron esta bloqueado")

            for dron in self.bloked_id_token:
                #Si el dron esta bloqueado
                if id_dron == dron["id"] and token == dron["token"]:
                    #enviar mensaje de error
                    #Encritar el mensaje con la clave publica del dron
                    response = {"status": "error", "message": "Dron bloqueado"}
                    #enviar respuesta al dron en formato json
                    conn.sendall(response.encode())
                    return True
        #Si el dron no esta bloqueado
        for dron in drones_registered:
            if str(dron["id"]) == str(id_dron):
                #Si el token es correcto y no ha expirado el tiempo de vida del token
                #imprimir toda la infor del dron
                if dron["token"] == token and dron["expiration"] > time.time()*1000:
                    self.inicioRestoHilos()
                    response = {"status": "success", "message": "Dron autenticado"}
                    #añadir al diccionario el dron y el token para bloquearlos
                    self.bloked_id_token.append({"id":id_dron,"token":token})
                    #ahora borramos el dron de la lista de drones registrados
                    drones_registered.remove(dron)
                    break       
                else:
                    if dron["expiration"] < time.time():
                        response = {"status": "error", "message": "Token expirado"}
                    else:
                        response = {"status": "error", "message": "Token incorrecto"}
                    break
                
        #enviar respuesta al dron en formato json
        response = json.dumps(response)
        #Regidtrar el evento de autenticacion
        self.registrar_evento("Autenticación de dron", f"Respuesta de autenticación: {response}", ip_origen=addr[0])
        conn.sendall(response.encode())

    
    def autenticate(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            self.engineMessagesToFront(f"Engine escuchando en {PORT}")
            
            while True:  # Mantener el Registry escuchando indefinidamente
                conn, addr = s.accept()
                with conn:
                    self.handle_connection(conn, addr)

    #Enviar al dron la clave publica del engine
    def enviar_clave_publica(self,conn, addr):
        
        with open('public_key.pem', 'rb') as file:
            public_key = serialization.load_pem_public_key(
                file.read(),
                backend=default_backend()
            )
        mensaje = (public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
        #Registar el evento de envio de clave publica
        self.registrar_evento("Envío de clave pública", "Clave pública enviada al dron", ip_origen=addr[0])
        conn.sendall(mensaje)
        self.engineMessagesToFront("Clave publica enviada al dron.")

####################################################################################################################


    #LISTO
    #################################################
    #Funciones para el Engine SHOW
    #################################################
    # Inicializar el producer de Kafka

    #Obtiene la clave publica del dron desde el archivo public_keys.json                       
    def encrypt_message(self, message,id):
        #Buscamos la clave publica del dron en el archivo public_keys.json
        encontrado = False
        with open(PUBLIC_KEYDRON_PATH, 'r') as file:
            public_keys = json.load(file)
        for key_info in public_keys:
            if key_info['id'] == id:
                try:
                    key = base64.b64decode(key_info['public_key'])
                    public_key = serialization.load_pem_public_key(key, backend=default_backend())
                except Exception as e:
                    print(f"Error cargando la clave: {e}")
                    self.engineMessagesToFront(f"Error cargando la clave: {e}")
                    self.registrar_evento("Error de encriptación", f"Error cargando la clave: {e}")
                
                try:
                    #Encriptamos el mensaje con la clave publica del dron
                    encrypted_message = public_key.encrypt(
                        message,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                    return encrypted_message

                except Exception as e:
                    self.registrar_evento("Error de encriptacion", f"Error {3}")
        
        return None
            

    

    def decrypt_message(self, encrypted_message):
        try:
            with open(PRIVATE_KEY_PATH, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            decrypted_message = private_key.decrypt(
                encrypted_message,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            self.engineMessagesToFront("Mensaje desencriptado exitosamente.")

            return decrypted_message
        except Exception as e:
            self.registrar_evento("Error al desencriptar mensaje",f"Error: {e}")
            return None
    
    def start_show(self):
        producer = KafkaProducer(
            bootstrap_servers=f'{HOST_BROKER}:{PORT_BROKER}', 
            value_serializer=lambda v: v
        )
        try:

            # Cargar el archivo JSON
            with open(FILENAME_FIGURAS, 'r') as file:
                data = json.load(file)
            
            # Iterar sobre las figuras en el JSON y enviar información al dron
            for figure in data['figuras']:
                #saber la cantidad de drones que se necesitan para la figura y guardarla en una variable
                drones_needed = len(figure['Drones'])
                for drone_info in figure['Drones']:
                    x_str, y_str = drone_info['POS'].split(',')
                    x = int(x_str)
                    y = int(y_str)
                    
                    # Usando wrap_coordinates para ajustar las coordenadas
                    x, y = self.wrap_coordinates(x, y)
                    
                    # Actualizar la posición en el drone_info
                    drone_info['POS'] = f"{x},{y}"
                    message = {
                        'ID_DRON': drone_info['ID'],
                        'COORDENADAS': drone_info['POS']
                    }
                    mensaje_encriptado = self.encrypt_message(json.dumps(message).encode(),drone_info['ID'])
                    if mensaje_encriptado is not None:
                        producer.send('engine_to_drons', key=str(drone_info['ID']).encode(), value=mensaje_encriptado)
                        self.registrar_evento("Mensaje enviado", f"Mensaje enviado a {drone_info['ID']}")
                    else:
                        #buscar si el dron esta bloqueado y si lo esta enviar un mensaje de error
                        for dron in self.bloked_id_token:
                            if dron["id"] == drone_info['ID']:
                                print("No se encontró la clave pública para el ID:", drone_info['ID'])

                                self.engineMessagesToFront("No se encontró la clave pública para el ID:", drone_info['ID'])
                                self.registrar_evento("Error de envío", f"No se encontró la clave pública para el ID {drone_info['ID']}")

                    #asegurarse del que el productor solo mande el mensaje una vez
                    producer.flush()
                while not self.all_drones_confirmed(drones_needed):
                    time.sleep(1)  # espera un segundo y vuelve a verificar
                    if self.weather == False:
                        self.engineMessagesToFront("Show terminado por condiciones climáticas.")
                        self.registrar_evento("Show terminado", "Show terminado por condiciones climáticas.")
                        self.backToBase()
                # Una vez que todos los drones han confirmado, limpia el conjunto para la siguiente figura
                self.confirmed_drones.clear()
                if self.weather == False:
                    self.engineMessagesToFront("Show terminado por condiciones climáticas.")
                    self.registrar_evento("Show terminado", "Show terminado por condiciones climáticas.")
                    self.backToBase()

                self.engineMessagesToFront("Todos los drones han confirmado.")
                self.registrar_evento("Confirmación de drones", "Todos los drones han confirmado.")
                time.sleep(5)  # Espera un segundo antes de enviar la siguiente figura
            time.sleep(10)  # Espera un segundo antes de terminar el show
            if self.weather == True:
                self.engineMessagesToFront("Todas las figuras han sido enviadas.")
                self.engineMessagesToFront("Show terminado exitosamente.")
                self.registrar_evento("Show terminado", "Todas las figuras han sido enviadas.")
                self.backToBase()

        except Exception as e:
            self.engineMessagesToFront("Error al enviar las figuras.")
            self.engineMessagesToFront(f"Error: {e}")
            self.registrar_evento("Error de envío", "Error al enviar las figuras.")

            # Aquí puedes manejar errores adicionales o emitir un mensaje según lo necesites.
        
        # Asegurarse de que todos los mensajes se envían
        producer.flush()
        producer.close()

    def all_drones_confirmed(self,drones_needed):
            print(f"CONFIRMED DRONES: {len(self.confirmed_drones)} - DRONES NEEDED: {drones_needed}")
            self.confirmDronToFront(f"CONFIRMED DRONES: {len(self.confirmed_drones)} - DRONES NEEDED: {drones_needed}")
            return len(self.confirmed_drones) == drones_needed

    def listen_for_confirmations(self):
        try:
            consumer = KafkaConsumer('listen_confirmation',
                                        bootstrap_servers=f'{HOST_BROKER}:{PORT_BROKER}',
                                        value_deserializer=lambda x: x)
            for message in consumer:
                    encrypted_message = message.value
                    key_encrypted = message.key.decode()
                    if key_encrypted == "DECRYPT":
                        decrypted_message = self.decrypt_message(encrypted_message)
                    if decrypted_message:
                        try:
                            message_data = json.loads(decrypted_message.decode('utf-8'))
                            if message_data['STATUS'] == 'LANDED':
                                drone_id = message_data['ID_DRON']
                                self.confirmed_drones.add(drone_id)
                        except json.JSONDecodeError:
                            self.engineMessagesToFront("Error al decodificar el mensaje JSON en zona de confirmacion.")
                            self.registrar_evento("Error de mensaje (listen_for_confirmations)", "Error al decodificar el mensaje JSON.")
                        except KeyError as e:
                            continue
                    else:
                        self.engineMessagesToFront("No se pudo desencriptar el mensaje.")

                        self.registrar_evento("Error de mensaje (listen_for_confirmations)", "No se pudo desencriptar el mensaje.")
                    
                        #actualizar el mapa

            consumer.commit()
            consumer.close()

            self.update_map(message.value)
        except Exception as e:
            print("Error al escuchar las confirmaciones de los drones.")
            print(f"Error: {e}")
            # Aquí puedes manejar errores adicionales o emitir un mensaje según lo necesites.
                  
            

    #LISTO
    #################################################
    def backToBase(self):
        #Contar todos los drones que estan en el show
        self.end_show()
        self.engineMessagesToFront("Todos los drones están volviendo a base.")

        #terminar el show
        self.engineMessagesToFront("El motor se apagará en breves instantes.")
        os._exit(0)
    #################################################
        
        

    #LISTO    
    #################################################
    #Funciones para escuhar los Drones
    #################################################
    def start_listening(self):

        try:
            consumer = KafkaConsumer('drons_to_engine',
                                        group_id='engine',
                                        bootstrap_servers=f'{HOST_BROKER}:{PORT_BROKER}',
                                        auto_offset_reset='earliest',
                                        value_deserializer=lambda x: x)

            for message in consumer:
                encrypted_message = message.value
                key_encrypted = message.key.decode()
                if key_encrypted == "DECRYPT":
                    decrypted_message = self.decrypt_message(encrypted_message)
                if decrypted_message:
                    try:
                        message_data = json.loads(decrypted_message.decode('utf-8'))
                        self.process_message(message_data)
                        self.registrar_evento("Mensaje recibido", f"Mensaje recibido de {message_data['ID_DRON']}")
                        
                        desencriptado = True
                    except KeyError as e:
                        self.registrar_evento("Error de mensaje (start_listening)", "Error en la clave del mensaje.")
                        print (f"Error: {e}")
                else:
                    self.registrar_evento("Error de mensaje (start_listening)", "No se pudo desencriptar el mensaje.")

            consumer.commit()
            consumer.close()
        except Exception as e:
            self.registrar_evento("Error de mensaje (start_listening)", "Error al escuchar los mensajes de los drones.")
            # Aquí puedes manejar errores adicionales o emitir un mensaje según lo necesites.

    #LISTO
    def load_last_updates(self):
        try:
            os.makedirs(os.path.dirname(FILENAME_ACTUALIZACIONES), exist_ok=True)
            with open(FILENAME_ACTUALIZACIONES, 'r') as file:
                data = json.load(file)
                if isinstance(data, dict):  # Si es un diccionario, lo convierte en una lista
                    return [data]
                else:
                    return data
        except FileNotFoundError:
            return []

    #LISTO
    def save_drones(self,drones):
        with open(FILENAME_ACTUALIZACIONES, 'w') as file:
            json.dump(drones, file, indent=4)

    #LISTO
    def process_message(self,message):
        # Extraer datos del mensaje
        #print(f"Received message structure: {message}")
        ID_DRON = message['ID_DRON']
        COORDENADA_X_ACTUAL = message['COORDENADA_X_ACTUAL']
        COORDENADA_Y_ACTUAL = message['COORDENADA_Y_ACTUAL']
        ESTADO_ACTUAL = message['ESTADO_ACTUAL']

        #Enviamos la informacion del dron al front end

    
        drones = self.load_last_updates()
        dron_found = False

        # Buscar si el dron ya está registrado y actualizar sus datos si es necesario
        for dron in drones:
            if dron["ID_DRON"] == ID_DRON:
                dron["COORDENADA_X_ACTUAL"] = COORDENADA_X_ACTUAL
                dron["COORDENADA_Y_ACTUAL"] = COORDENADA_Y_ACTUAL
                dron["ESTADO_ACTUAL"] = ESTADO_ACTUAL
                dron_found = True
                #Terminar el bucle una vez que se actualiza el dron
                break

        # Si el dron no fue encontrado en la lista, añadirlo
        if not dron_found:
            drones.append({
                "ID_DRON": ID_DRON,
                "COORDENADA_X_ACTUAL": COORDENADA_X_ACTUAL,
                "COORDENADA_Y_ACTUAL": COORDENADA_Y_ACTUAL,
                "ESTADO_ACTUAL": ESTADO_ACTUAL
            })


        #Si el estado actual del dron es LANDED O FLYING, actualizar el mapa
        #if ESTADO_ACTUAL == "MOVING" or ESTADO_ACTUAL == "LANDED":
        self.update_map(message)


        self.save_drones(drones)  # Guardar la lista actualizada de drones


    #LISTO
    #################################################
    #Comunicacion con el Servidor de Clima
    #################################################
    def get_weather(self, city):
        # Comunicarse con el servicio de clima y obtener la temperatura
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((CLIMATE_SERVICE_HOST, CLIMATE_SERVICE_PORT))
            s.sendall(city.encode())
            data = s.recv(1024)
            weather_data = json.loads(data.decode())
            return weather_data

    def perform_action_based_on_weather(self, city):
        weather_data = self.get_weather(city)
        temperature = int(weather_data["temperature"])
        
        if temperature != "Unknown":
            print(f"La temperatura en {city} es de {temperature} grados.")
            self.engineMessagesToFront(f"La temperatura en {city} es de {temperature} grados.")
            self.registrar_evento("Clima", f"Datos del clima recibidos para {city}" )
            
            # Si la temperatura está en el rango agradable, el show continúa.
            if TEMPERATURE_COMFORTABLE_LOW <= temperature <= TEMPERATURE_COMFORTABLE_HIGH:
                self.engineMessagesToFront("Las condiciones climáticas son agradables, el show continua")
            # Si la temperatura es demasiado fría o demasiado caliente, se recomienda terminar el show.
            elif temperature < TEMPERATURE_COLD_LIMIT or temperature > TEMPERATURE_HOT_LIMIT:
                self.engineMessagesToFront("Advertencia: condiciones climáticas extremas detectadas.")
                self.send_weather_alert(city, temperature)
            else:
                self.engineMessagesToFront("Las condiciones climáticas están fuera de lo ideal, pero no son extremas.")
        else:
            self.engineMessagesToFront("Datos del clima desconocidos.")
    def send_weather_alert(self, city, temperature):
        # Envía una alerta a un sistema o componente que maneja las operaciones del show

        self.engineMessagesToFront(f"Alerta: Condiciones climáticas no adecuadas en {city}. Temperatura: {temperature} grados.")
        self.engineMessagesToFront("Enviando alerta al sistema de operaciones del show...")

        self.registrar_evento("Alerta de clima", f"Condiciones climáticas extremas detectadas en {city}. Temperatura: {temperature} grados.")
        self.end_show()
        self.weather = False

    def check_weather_periodically(self, city):
        
        while self.weather == True and self.city != None:
            print(f"Chequeando el clima para la ciudad: {city}")

            self.engineMessagesToFront(f"Chequeando el clima para la ciudad: {city}")

            self.perform_action_based_on_weather(city)
            time.sleep(10)
            self.registrar_evento("Chequeo de clima", "Chequeo de clima realizado.")

    #LISTO
    #################################################
    #Funciones para el Engine MENU
    #################################################
    #Produce mensaje en el topic end_show para que los drones sepan que deben terminar el show
    #El mensaje es enviado a todos los drones
    def end_show(self):
        producer = KafkaProducer(
            bootstrap_servers=f'{HOST_BROKER}:{PORT_BROKER}', 
            value_serializer=lambda v: json.dumps(v).encode('utf-8'))

        message = {
                'END_SHOW': 'True'
            }
        producer.send('end_show', value=message)
        producer.flush()
        producer.close()
        
        self.engineMessagesToFront("Fin del show")
        self.registrar_evento("Fin del show", "Mensaje de fin de show enviado a los drones.")
        
    
    #LISTO
    def inicioRestoHilos(self):
        self.show_thread = threading.Thread(target=self.start_show)
        self.dron_update_thread = threading.Thread(target=self.start_listening)
        self.map_display_thread = threading.Thread(target=self.display_map)
        self.dron_landed_confirmation_thread = threading.Thread(target=self.listen_for_confirmations)
        # Iniciar los hilos
        self.show_thread.start()
        self.dron_update_thread.start()
        self.map_display_thread.start()
        self.dron_landed_confirmation_thread.start()

    def is_city(self, city_name):
        geolocator = Nominatim(user_agent="city_verifier")
        try:
            location = geolocator.geocode(city_name, exactly_one=True)
            if location:

                print(f"La ciudad {city_name} es válida.")
                self.registrar_evento("Ciudad válida", f"La ciudad {city_name} es válida.")
                return True
            else:
                print("No se encontró ninguna ubicación.")
                return False
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Error al geocodificar: {e}")
            return False
        

    def start_engine(self):
        # Iniciar los métodos en hilos separados

            # Asegúrate de obtener la ciudad antes de iniciar el hilo meter en self.ciudad
            # Solicitar una ciudad válida antes de iniciar el motor
            while True:
                self.city = input("Ingrese la ciudad: ")
                if self.is_city(self.city):
                    break
                else:
                    print("Ingrese una ciudad válida.")
            
            #Si la ciudad no es una cadena de letras entonces volver a solicitar

            self.weather = True

            #Llamar a la funcion para crear las claves publicas y privadas
            self.generate_keys()

            # Inicializar los hilos con banderas de detención
            self.weather_thread = threading.Thread(target=self.check_weather_periodically, args=(self.city,))
            self.auth_thread = threading.Thread(target=self.autenticate)
            
            # ... Iniciar los hilos
            self.weather_thread.start()
            self.auth_thread.start()

            self.engineMessagesToFront("Motor iniciado")
            self.registrar_evento("Motor iniciado", "Motor de la aplicación iniciado.")


    
    
           
    #AUDITORIA DE SEGURIDAD
    #################################################
    #Funciones para la auditoria de seguridad
    #################################################
    def obtener_ip(self):
        #Obtiene la IP de la máquina local.
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except Exception as e:
            return f"Error obteniendo IP: {e}"


    def registrar_evento(self, evento, descripcion, ip_origen="Desconocida"):
        #Registra un evento de auditoría.
        fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if ip_origen == "Desconocida":
            ip = self.obtener_ip()
        else:
            ip = ip_origen

        log_entry = f"{fecha_hora} | IP Local: {self.obtener_ip()} | IP Origen: {ip} | Evento: {evento} | Descripción: {descripcion}"
        self.logger.info(log_entry)
        #Transformar en json
        log_entry = {
            "fecha_hora": fecha_hora,
            "ip_local": self.obtener_ip(),
            "ip_origen": ip,
            "evento": evento,
            "descripcion": descripcion
        }
        #Enviar el mensaje al front end si esta conectado
        if(self.is_server_available(f"http://{HOST_FRONT}:{PORT_FRONT}/")):
            self.sendLogs(json.dumps(log_entry))

    #################################################
        
    #################################################
    # Exposicion de API para crear un front end
    #################################################
    #Conectarse al front end y enviar el mapa
    def is_server_available(self, url):
        try:
            response = requests.get(url, timeout=5)  # Ajusta el timeout según sea necesario
            return response.status_code == 200
        except requests.RequestException:
            return False        
    
    def sendMap(self):
        if(self.is_server_available(f"http://{HOST_FRONT}:{PORT_FRONT}/")):
            try:
                url = f"http://{HOST_FRONT}:{PORT_FRONT}/map"
                #Enviar el display del mapa2 al front end
                # Convertir grid_data en un JSON y enviarlo al front end
                headers = {'Content-Type': 'application/json'}
                auditData = json.dumps({'mapHtml': self.mapa2.display()})
                requests.post(url, data=auditData, headers=headers)
            except Exception as e:
                print(f"Error al enviar el mapa al front end")
                self.registrar_evento("Error de mensaje (sendMap)", "Error al enviar el mapa al front end.")
        else:
            self.registrar_evento("Error de conexión", "El servidor del front end no está disponible.")
    
            
    #Coonectarse al front end y enviar las actualizaciones
    def sendUpdatesOfDrones(self,message):
        if(self.is_server_available(f"http://{HOST_FRONT}:{PORT_FRONT}/")):
            try:
                url = f"http://{HOST_FRONT}:{PORT_FRONT}/drones"
                #Enviar los mensajes al front end
                headers = {'Content-Type': 'application/json'}
                requests.post(url, json.dumps(message),headers=headers)
            except Exception as e:
                print(f"Error al enviar los mensajes al front end")
                self.registrar_evento("Error de mensaje (sendUpdatesOfDrones)", "Error al enviar mensaje al front end.")
        else:
            self.registrar_evento("Error de conexión", "El servidor del front end no está disponible.")

    #Conectarse al front end y enviar mensajes que genera el motor
    def sendLogs(self,message):
        if(self.is_server_available(f"http://{HOST_FRONT}:{PORT_FRONT}/")):
            try:
                url = f"http://{HOST_FRONT}:{PORT_FRONT}/audit"
                #Enviar los mensajes al front end
                headers = {'Content-Type': 'application/json'}
                requests.post(url, message,headers=headers)
            except Exception as e:
                print(f"Error al enviar los mensajes al front end")
                self.registrar_evento("Error de mensaje (confirmDronToFront)", "Error al enviar mensaje al front end.")
        else:
            self.registrar_evento("Error de conexión", "El servidor del front end no está disponible.")
    
    def engineMessagesToFront(self,message):
        if(self.is_server_available(f"http://{HOST_FRONT}:{PORT_FRONT}/")):
        
            try:
                #convetir el mensaje en un diccionario 
                messageJson = {"message":message}
                url = f"http://{HOST_FRONT}:{PORT_FRONT}/engine"
                #Enviar los mensajes al front end
                headers = {'Content-Type': 'application/json'}
                requests.post(url,json.dumps(messageJson),headers=headers)
            except Exception as e:
                print(f"Error al enviar los mensajes al front end")
                self.registrar_evento("Error de mensaje (confirmDronToFront)", "Error al enviar mensaje al front end.")
        else:
            self.registrar_evento("Error de conexión", "El servidor del front end no está disponible.")
    def confirmDronToFront(self,message):
        if(self.is_server_available(f"http://{HOST_FRONT}:{PORT_FRONT}/")):
            try:
                #convetir el mensaje en un diccionario 
                messageJson = {"message":message}
                url = f"http://{HOST_FRONT}:{PORT_FRONT}/confirmed"
                #Enviar los mensajes al front end
                headers = {'Content-Type': 'application/json'}
                requests.post(url,json.dumps(messageJson),headers=headers)

            except Exception as e:
                print(f"Error al enviar los mensajes al front end")
                self.registrar_evento("Error de mensaje (confirmDronToFront)", "Error al enviar mensaje al front end.")
        else:
            self.registrar_evento("Error de conexión", "El servidor del front end no está disponible.")
    #LISTO        
    def menu(self):

        print("Bienvenido al motor de la aplicación de drones.")
        print("Seleccione una opción: ")
        print("1. Iniciar el motor")
        print("2. Salir")
        option = input("Ingrese la opción: ")
        if option == "1":
            self.start_engine()
        elif option == "2":
            print("Saliendo del motor...")
            os._exit(0)
            
        else:
            print("Opción inválida")
            self.menu()

#main de prueba
def main():  
    try:
        engine = Engine()
    
        with open(FILENAME_ACTUALIZACIONES, 'w') as file:
            json.dump([], file, indent=4)
        engine.menu()
    #Si se presiona la letra q se detiene el motor y se limpia
    except KeyboardInterrupt:
        engine.restart()
        print("Programa terminado por el usuario.")    


if __name__ == "__main__":
    main()






    




