import json
import socket
import sys
import os  # Nuevo
import threading  # Nuevo
import requests  # Nuevo



class AD_WEATHER:
    def __init__(self, weather_file,host,port):
        # Inicializa la instancia con la ubicación del archivo de clima.
        self.weather_file = weather_file
        self.engine_host = host
        self.engine_port = port

    def load_weather_data(self):
        # Carga la ciudad y la devuelve como un string.
        try:
            with open(self.weather_file, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            # Si el archivo no existe, imprime un mensaje de error y retorna None.
            print("Archivo de clima no encontrado.")
            return None
    
    def get_city(self):
        # Obtiene el nombre de la ciudad del archivo de clima.
        weather_data = self.load_weather_data()
        if weather_data:
            return weather_data.get("city")
        return None

    def save_city(self, city):
        #Guarda el nombre de la ciudad en el archivo de clima y la temperatura actual.
        weather_data = self.load_weather_data()
        #Si el archivo de clima no existe, lo crea con la ciudad,solo podra haber una ciudad
        if not weather_data:
            weather_data = {}
        weather_data["city"] = city
        with open(self.weather_file, 'w') as file:
            json.dump(weather_data, file)
        
        
    

    def start_server(self):
        solicitudInicial = 0
        #Limpiar de datos el archivo de clima
        weather_data = self.load_weather_data()
        if weather_data:
            weather_data.clear()
            with open(self.weather_file, 'w') as file:
                json.dump(weather_data, file)

        # Inicia el servidor de clima en el host y puerto especificados.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.bind((self.engine_host, self.engine_port))
                server_socket.listen()
                print(f"Servidor de clima escuchando en {self.engine_host}:{self.engine_port}")

                while True:
                    try:
                        client_socket, addr = server_socket.accept()
                    except socket.error as e:
                        print(f"Error al aceptar conexiones: {e}")
                        continue
            
                    with client_socket:
                        print(f"Conexión desde {addr}")
                        while True:
                            try:
                                city_bytes = client_socket.recv(1024)
                                if not city_bytes:
                                    print(f"Engine desconectado: {addr}")
                                    break
                                city = city_bytes.decode()
                                #Si es la primera solicitud, guardamos la ciudad en el archivo de clima
                                if solicitudInicial == 0:
                                    self.save_city(city)
                                    weather_data = self.get_weather_from_api(city)
                                    client_socket.sendall(json.dumps(weather_data).encode())
                                    solicitudInicial = 1
                                else:
                                    #si la ciudad es diferente a la que ya esta guardada, la guardamos en el archivo de clima
                                    if city != self.get_city():
                                        self.save_city(city)
                                    weather_data = self.get_weather_from_api(self.get_city())
                                    client_socket.sendall(json.dumps(weather_data).encode())
                            except socket.error as e:
                                print(f"Error al comunicarse con el Engine: {e}")
                                break
                            except json.JSONDecodeError as e:
                                print(f"Error al decodificar datos JSON: {e}")
                                break

        except socket.error as e:
            print(f"No se pudo iniciar el servidor de clima en {self.engine_host}:{self.engine_port}: {e}")
            sys.exit(1)  # Sale del programa si no puede iniciar el servidor.
    
    #Definimos una funcion que se encarga de consultar el clima de una ciudad a una API externa
    def get_weather_from_api(self, city):
        #URL de la API de clima
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={'9c05b8985987832b91fc9419f7a8737e'}&units=metric"
        try:
            #Realizamos la peticion GET a la API
            response = requests.get(url)
            #Si la peticion fue exitosa
            if response.status_code == 200:
                #Obtenemos los datos de la respuesta
                data = response.json()
                #Retornamos la temperatura de la ciudad como un diccionario
                print ("La temperatura de la ciudad es: ", data["main"]["temp"] , "°C")
                return {"temperature": data["main"]["temp"]}
            else:
                #Si la peticion no fue exitosa, retornamos None
                print(f"Error al consultar la API de clima: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            #Si ocurre un error al realizar la peticion, retornamos None
            print(f"Error al consultar la API de clima: {e}")
            return None
    

def main():
    # Crea una instancia de la clase AD_WEATHER y la inicializa.
    weather_engine = AD_WEATHER(
    "weather_conditions.json",
    os.getenv('HOST_WEATHER', 'weather'),
    int(os.getenv('PORT_WEATHER'))
)
    # Iniciamos el servidor de clima desde un hilo
    threadWeather = threading.Thread(target=weather_engine.start_server)
    threadWeather.start()

    # Iniciamos el cambio de temperatura desde un hilo
    threadChangeTemperature = threading.Thread(target=weather_engine.change_temperature)
    threadChangeTemperature.start()


if __name__ == "__main__":
    main()
