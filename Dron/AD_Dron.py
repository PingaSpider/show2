import socket
import os
import json
import threading
import time
from kafka import KafkaConsumer, KafkaProducer
from Mapa import Mapa  # Ahora puedes importar Mapa
import colorama
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding as asy_padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import urllib3
import base64
import requests





HOST_REGISTRY = os.getenv('HOST_REGISTRY')
PORT_REGISTRY = int(os.getenv('PORT_REGISTRY'))

PORT_ENGINE = int(os.getenv('PORT_ENGINE'))
HOST_ENGINE = os.getenv('HOST_ENGINE')

HOST_BROKER = os.getenv('HOST_BROKER')
PORT_BROKER = os.getenv('PORT_BROKER')

PORT_ENGINE2 = int(os.getenv('PORT_ENGINE2'))

# Estados posibles del dron
STATES = ["WAITING", "MOVING", "LANDED"]
COLORS = ["rojo", "verde"]

PUBLIC_KEY_PATH = '/app/public_key.pem'
PRIVATE_KEY_PATH = '/app/private_key.pem'
PUBLIC_KEY_ENGINE = '/app/public_key_engine.pem'
CERTIFICATE_PATH = '/app/certificate.crt'
CLAVE_AES = 'clave/claveCifrada.json'

CONTADOR = 0


class Dron:
    
    def __init__(self):
        # Asigna el siguiente ID disponible al dron y luego incrementa el contador
        self.id = 1
        self.token = None  # Inicialmente, el dron no tiene un token hasta que se registre
        self.state = STATES[0] # Inicialmente, el dron está en estado "waiting"
        self.position = (1,1) # Inicialmente, el dron está en la posición (1,1)
        self.color = COLORS[0] # Inicialmente, el dron está en estado "waiting"
        self.showState = True #Variable para saber si el dron esta en el show o no
        self.autenticated = False #Variable para saber si el dron esta autenticado o no
    
    #Define el destructor del dron (no imprima nada en el destructor)
    def destroy(self):
        pass

    #Definir los getters y setters para los atributos del dron
    def get_id(self):
        return self.id
    
    def get_token(self):
        return self.token
    
    def get_state(self):
        return self.state
    
    def get_position(self):
        return self.position
    
    def set_id(self, id):
        self.id = id
    
    def set_token(self, token):
        self.token = token
    
    def set_state(self, state):
        self.state = state
    
    def set_position(self, position):
        self.position = position
    
    #definimos una encriptacion para los mensajes que se envian al engine con una llave privada y publica
    ##########ZONA DE REGISTRO Y AUTENTICACION##################3
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

    

    # Método para registrar el dron en el Registry
    def register(self):
        url = f"https://{HOST_REGISTRY}:{PORT_REGISTRY}/drones/register"
        headers = {'Content-Type': 'application/json'}
        payload = json.dumps({'id': self.id})       
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            response = requests.post(url,headers=headers,data=payload,verify=False, timeout=10)
            if response.status_code == 201:
                #si el mensaje es Dron registrado con exito imprimimos el mensaje
                if response.json()['message'] == 'Dron registrado con exito':
                    print("Dron registrado con exito.")
                    self.token = response.json()['token']
                    print()
                    return True
                else:
                    #imprimimos que se ha actualizado el token
                    print("Token actualizado.")
                    self.token = response.json()['token']
                    print()
                    return True
            else:
                if response.status_code == 202:
                    #El dron ya esta registrado
                    print("El dron ya esta registrado y token aun válido.")
                    print()
                else:
                    print("Error al registrar el dron.")
                    return False
        except requests.exceptions.RequestException as e:
            print("Error de conexión con el Registry:", e)
            return False

    #Enviar la clave publica del dron al Engine antes de unirnse al show
    def enviarPublicKey(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST_ENGINE, PORT_ENGINE))
                
                #Leemos la clave publica del dron
                with open('public_key.pem', 'rb') as f:
                    public_key_bytes = f.read()
                mensaje = public_key_bytes

                #pasamos la public key a un str para poder enviarla encriptada correctamente
                s.sendall(mensaje)
                print("Clave publica enviada al Engine.")
                s.close()
                return True
            except Exception as e:
                print("Error al tratar de enviar la clave publica al Engine.")
                print(e)
                s.close()
                return False
    
    #Solicitar al Engine su clave publica LISTO
    def solicitar_public_key(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                print("Conectando con el Engine para obtener la clave publica")
                s.connect((HOST_ENGINE, PORT_ENGINE))
                #Enviamos un mensaje al Engine para obtener la clave publica
                reg_msg = {'message': 'Obtener clave publica'}
                message = self.cifrarPrimerMensaje(json.dumps(reg_msg).encode())
                s.sendall(message) 
                
                data = s.recv(1024)
                if not data:  # Si no se recibe respuesta, imprimir un error y retornar False
                    print("No se recibió la clave publica del Engine.")
                    #cerrar la conexion
                    s.close()
                    return False
                else:
                    #cerrar la conexion
                    s.close()
                    print("Clave publica recibida.")
                    #Guardamos la clave publica en un archivo para futuras conexiones
                    os.makedirs(os.path.dirname(PUBLIC_KEY_ENGINE), exist_ok=True)
                    with open(PUBLIC_KEY_ENGINE, 'wb') as f:
                        f.write(data)

                    # Convertir la clave pública en formato PEM a un objeto de clave pública
                    public_key = serialization.load_pem_public_key(data, backend=default_backend())
                    print("Clave publica Engine guardada")
                    #Retornamos la clave public
                    return public_key
            except Exception as e:
                print("Error al tratar de recibir la clave publica del Engine.")
                print(e)
                #cerrar la conexion
                s.close()
    #Metodo para autenticar el dron con el Engine (usar el token) y
                
    def cifrarPrimerMensaje(self, mensaje):
        # Leer la clave desde el archivo JSON
        # Generar una clave segura para AES-256
        clave = os.urandom(32)  # 32 bytes para AES-256

        # Codificar la clave en base64 para almacenamiento en JSON
        clave_aes_base64 = base64.b64encode(clave).decode('utf-8')

        # Guardar la clave cifrada en un archivo JSON
        with open(CLAVE_AES, 'w') as f:
            json.dump({'clave': clave_aes_base64}, f)
        
        # Crear un vector de inicialización aleatorio
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(clave), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        cifrado = encryptor.update(mensaje) + encryptor.finalize()
        # Prependemos "AES-CFB:" como identificador del algoritmo usado
        return b"AES-CFB:" + iv + cifrado
        

    def autenticate(self):

        keyEngine = self.solicitar_public_key()
        #Si no se recibe la clave publica del Engine
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                #Conectamos con el Engine
                s.connect((HOST_ENGINE, PORT_ENGINE))

                #Creamos un mensaje con el id del dron, el token y la clave publica del dron
                reg_msg = {'id': self.id, 'token': self.token}
                #convertimos el mensaje a un JSON
                reg_msg = json.dumps(reg_msg).encode()

                #Encriptamos el mensaje con la clave publica del Engine
                print("Encriptando mensaje...")
                encrypted_data = keyEngine.encrypt(
                    reg_msg,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                #Enviamos el mensaje encriptado al Engine
                s.sendall(encrypted_data)
                print("Solicitud de autenticación enviada al Engine.")
                
                #########Recibimos la respuesta del Engine#########
                #Recibimos la respuesta del Engine
                data = s.recv(1024)

                #Si no se recibe respuesta del Engine
                if not data:
                    print("No se recibió respuesta del Engine en la autenticación.")
                    self.autenticated = True
                    return True
                
                    
                #Convertimos la respuesta a un JSON
                response = json.loads(data.decode())

                #Si la respuesta es un JSON valido
                if response['status'] == 'success':
                    print(f"Autenticado exitosamente")
                    s.close()
                    self.enviarPublicKey()
                    self.autenticated = True
                    #
                    return True
                #Si la respuesta no es un JSON valido
                else:
                    #Si el mensaje es "Token expirado"
                    if response['message'] == 'Token expirado':
                        print(f"Error al Autenticar.El token ya expiro.")
                        s.close()
                        return True
                    #Si el mensaje es otro diferente a "Token expirado"
                    else:
                        print(f"Error al Autenticar: " + response['message'])
                        s.close()
                        return True                    
            except Exception as e:
                print("Error al conectarse con el Engine o al encriptar el mensaje")
                print(e)
                s.close()
                return True
    ###########################################################
            

   
#################################################
#Comunicacion del Engine con el Dron
#################################################


 #Buscamos la clave publica del dron en el archivo public_keys.json
    def encrypt_message(self, message):
        # Cargar la clave pública del engine
        try:
            with open(PUBLIC_KEY_ENGINE, 'rb') as f:
                public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
        except Exception as e:
            print("Error al cargar la clave publica del Engine: ", e)
            return None             
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
            print(f"Error encriptando el mensaje: {e}")
        
        return None

#LISTO
# El dron necesita saber su propio ID para suscribirse al tópico correcto.
    def decrypt_message(self, mensaje):
        # Cargar la clave privada del dron
        try:
            with open(PRIVATE_KEY_PATH, 'rb') as f:
                private_key= serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
        except Exception as e:
            print("Error al cargar la clave privada: ", e)
            return None
        try:
            decrypted_data = private_key.decrypt(
                mensaje,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            print("Mensaje desencriptado para procesar movimiento")
            return decrypted_data
        except Exception as e:
            return None
        

    
    def recive_data(self):
        try:
            consumer = KafkaConsumer(
                'engine_to_drons',
                group_id='dron_group_' + str(self.id),
                bootstrap_servers=f'{HOST_BROKER}:{PORT_BROKER}',
                auto_offset_reset='earliest',
                value_deserializer=lambda x: x
            )
            for message in consumer:
                encrypted_message = message.value # Necesitas acceder al valor del mensaje
                drone_id = message.key.decode()  # Correcto
                if drone_id == str(self.id):  # Asegúrate de convertir self.id a str si es necesario
                    decrypted_message = self.decrypt_message(encrypted_message)
                    if decrypted_message is not None:
                        decrypted_message = decrypted_message.decode('utf-8')
                        message_data = json.loads(decrypted_message)
                        self.process_message(message_data)
                    else:
                        print("Error al procesar el mensaje del Engine")
        except Exception as e:
            print("Error en la conexión de Kafka: ", e)
    
    # Función que procesa el mensaje y llama al método run
    def process_message(self,message):

        data = message
        if data['ID_DRON'] == self.id:
            ID_DRON = data['ID_DRON']
            COORDENADAS = data['COORDENADAS'].split(",")
            COORDENADA_X_OBJETIVO = int(COORDENADAS[0])
            COORDENADA_Y_OBJETIVO = int(COORDENADAS[1])
            # Si el ID del dron en el mensaje coincide con el ID del dron actual, procesar el mensaje
            self.run((COORDENADA_X_OBJETIVO, COORDENADA_Y_OBJETIVO))
    
    # Método para mover el dron un paso hacia el objetivo
    def move_one_step(self, target_position):
        # Descomponer las coordenadas actuales y objetivo
        x_current, y_current = self.position
        x_target, y_target = target_position
        
        # Determinar la dirección del movimiento en el eje X
        if x_current < x_target:
            x_current += 1
        elif x_current > x_target:
            x_current -= 1

        # Determinar la dirección del movimiento en el eje Y
        if y_current < y_target:
            y_current += 1
        elif y_current > y_target:
            y_current -= 1

        # Actualizar la posición del dron
        self.position = (x_current, y_current)

    # Método para mover el dron a las coordenadas objetivo    
    def run(self, target_position):
    # Moverse hacia la posición objetivo un paso a la vez
        self.state = STATES[1]
        self.color = COLORS[0]
        while self.position != target_position:
            time.sleep(2)
            self.move_one_step(target_position)
            
            print(f"P:{self.position}, S: {self.state}, M: {target_position}")
            
            # Enviar una actualización al engine después de cada movimiento
            self.send_update()

            # Pausa de un segundo
            if self.showState == False:
                break
        
        if self.showState == False:
            return self.backTobase()
        
        self.state = STATES[2]
        self.color = COLORS[1]
        self.send_update()
        self.send_confirmation()
    
    def backTobase(self):
        self.state = STATES[1]
        while self.position != (1,1):
            self.move_one_step((1,1))
            print(f"P:{self.position}, S: {self.state}, M: {(1,1)}")
            time.sleep(2)

        print("Aterrizado en la base...")
        print("Mis parametros de vuelta a la base son: ")
        self.state = STATES[0]
        self.color = COLORS[0]
        self.showState = True
        #Posiciion actual
        print(f"Posicion actual: {self.position}")
        #Estado actual
        print(f"Estado actual: {self.state}")
        #Color actual
        print(f"Color actual: {self.color}")
        print(f"Mi ID es: {self.id}")
        print(f"Mi token es: {self.token}")
        print()
        print()
        #volver al Menu
        return True

        
    
    def endShow(self):
        #Crear consumidor con el topic end_show y el id del dron
        consumer = KafkaConsumer(
            'end_show',
            group_id=f"dron_group_{self.id}",
            bootstrap_servers = f'{HOST_BROKER}:{PORT_BROKER}',
            auto_offset_reset='earliest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        # Consumir mensajes de Kafka
        for message in consumer:
            encrypted_message = message.value # Necesitas acceder al valor del mensaje
            drone_id = message.key.decode()  # Correcto
            if drone_id == str(self.id):  # Asegúrate de convertir self.id a str si es necesario
                decrypted_message = self.decrypt_message(encrypted_message)
                if decrypted_message is not None:
                    decrypted_message = decrypted_message.decode('utf-8')
                    message_data = json.loads(decrypted_message)
                else:
                    print("Error al procesar el mensaje del Engine")
            # message = {'END_SHOW': 'True'}
            if message_data['END_SHOW'] == 'True':
                self.showState = False
                print("END SHOW")
                break
            consumer.commit()
        consumer.close()
        print("Show Terminado volviendo a la base...")
        print()
        return self.backTobase()

    

#################################################
        
#LISTO
#################################################
#Comunicacion del Dron con el Engine
#################################################
# Método para enviar una actualización al Engine
    def send_update(self):
        # Crear el productor de Kafka
        producer = KafkaProducer(
            bootstrap_servers = f'{HOST_BROKER}:{PORT_BROKER}',
            value_serializer=lambda v: v
        )
        
        # Preparar el mensaje en formato JSON
        message = {
            'ID_DRON': self.id,
            'COORDENADA_X_ACTUAL': self.position[0],
            'COORDENADA_Y_ACTUAL': self.position[1],
            'ESTADO_ACTUAL': self.state,
            'COLOR': self.color
        }

        message_encrypted = self.encrypt_message(json.dumps(message).encode('utf-8'))
        # Enviar el mensaje al tópico drones_to_engine
        producer.send('drons_to_engine',key=str("DECRYPT").encode(), value=message_encrypted)
        
        
        # Cerrar el productor
        producer.close()
        
        # Emitir el mensaje en pantalla
        print("SEND_UPDATE ID de Dron: ", self.id)
    
    # Método para enviar una confirmación al Engine
    def send_confirmation(self):
        producer = KafkaProducer(
            bootstrap_servers = f'{HOST_BROKER}:{PORT_BROKER}',
            value_serializer=lambda v: v
        )
        message = {
            'ID_DRON': self.id,
            'STATUS': self.state,
            'COORDENADAS': f"{self.position[0]},{self.position[1]}",
            'COLOR': self.color       
        }
        message_encrypted = self.encrypt_message(json.dumps(message).encode('utf-8'))
        # Enviar el mensaje al tópico drones_to_engine
        producer.send('listen_confirmation',key=str("DECRYPT").encode(), value=message_encrypted)
        producer.close() # Cerrar el productor
        
        print(f"SEND_CONFIRMATION: {self.state} y color {self.color}")
        print("Esperando más instrucciones...")

        


####################################################################
    def run_dron(self):
        if self.autenticated:
            # Iniciar los métodos en hilos separados
            thread1 = threading.Thread(target=self.recive_data)
            thread2 = threading.Thread(target=self.send_update)
            thread3 = threading.Thread(target=self.send_confirmation)
            thread4 = threading.Thread(target=self.endShow)

            thread1.start()
            thread2.start()
            thread3.start()
            thread4.start()
            return True
        else:
            print("Dron no autenticado: Debe autenticar el dron antes de unirse al show.")
            return True
    
            


def solicitar_id():
    id = 0
    while True:
        try:
            id = int(input("Ingrese el id del dron: "))
            if id > 0 and id <= 100:
                print()
                return id
            else:
                print("El id debe ser un número entre 1 y 100")
        #Si el id no es un numero entero se seguira pidiendo el id una y otra vez en un ciclo
        except ValueError:
            print("El id debe ser un número entero")
            continue


#llamar al menu con el dron
def menu(dron):
    global CONTADOR
    if CONTADOR == 0:
        id = solicitar_id()
        dron.set_id(id)
        CONTADOR += 1
    
    #Vaciar el json de la clave cifrada
    with open(CLAVE_AES, 'w') as f:
        json.dump({}, f)
    #Imprimir el menu
    print("Bienvenido al menu del Dron")   
    while True:
        print("1. Registrar Dron")
        print("2. Autenticar Dron")
        print("3. Unirse al Show")
        print("4. Salir")
        print()
        #esperar por el input del usuario
        opcion = input("Ingrese una opcion: ")


        if opcion == "1":
            dron.register()
        elif opcion == "2":
            dron.generate_keys()
            dron.autenticate()
        elif opcion == "3":
            dron.run_dron()
        elif opcion == "4":
            print("Saliendo...")
            break
        else:
            print()
            print("Opcion no valida")
            print()

def main():
    
    # Crear un nuevo dron con un id aleatorio entre 1 y 100
    dron = Dron()
    menu(dron)
    print("Fin del programa el dron con id: ", dron.get_id(), " ha terminado su ejecucion.  ")     
    os._exit(0)
    
if __name__ == '__main__':
    #menu()
    main()