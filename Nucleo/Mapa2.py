import colorama
import re

class Mapa2:

    def __init__(self, size=20):
        self.size = size
        self.grid = [[' ' * 2 for _ in range(size)] for _ in range(size)]
        
        # Establece los bordes con un punto y de fondo azul
        for i in range(size):
            punto_str = '--'  # Asegura que el punto tenga dos espacios
            self.grid[0][i] = f'<span style="background-color: blue; color: white;">{punto_str}</span>'
            self.grid[size - 1][i] = f'<span style="background-color: blue; color: white;">{punto_str}</span>'
            self.grid[i][0] = f'<span style="background-color: blue; color: white;">{punto_str}</span>'
            self.grid[i][size - 1] = f'<span style="background-color: blue; color: white;">{punto_str}</span>'

        
        self.drones_positions = {}
        self.dron_solapado = {}


    def place_drone(self, x, y, id, color):
        # Coloca el dron en la posición indicada en la cuadrícula del mapa en html
        id_str = str(id).zfill(2)  # Asegura que el ID tenga dos dígitos

        #si el codigo  de color es rojo se pone el fondo rojo y el texto blanco para html
        if color == "rojo":
            self.grid[y][x] = f'<span style="background-color: red; color: white;">{id_str}</span>'
        #si el codigo  de color es azul se pone el fondo azul y el texto blanco para html
        elif color == "amarillo":
            self.grid[y][x] = f'<span style="background-color: yellow; color: black;">{id_str}</span>'
        #si el codigo  de color es verde se pone el fondo verde y el texto blanco para html
        else:
            self.grid[y][x] = f'<span style="background-color: green; color: white;">{id_str}</span>'
        


    def display(self):
        # Construye HTML con la cuadrícula completa
        html_output = '<div style="font-family: monospace;">'
        for row in self.grid:
            html_output += '<div>'
            for cell in row:
                if cell.strip():
                    html_output += cell
                else:
                    html_output += '&nbsp;&nbsp;'  # Espacios para celdas vacías
            html_output += '</div>'
        html_output += '</div>'
        # Retorna el HTML completo
        return html_output
    
    def update_position(self, new_x, new_y, id, color):
        # Verifica si la posición está dentro del mapa
        if new_x < 0 or new_x >= self.size or new_y < 0 or new_y >= self.size:
            raise ValueError("Posición inválida")

        # Verifica si el dron ya está en el mapa y obtiene su posición anterior
        old_position = self.drones_positions.get(id)
        if old_position:
            old_x, old_y, _ = old_position
            # Revisa si había otros drones en la posición anterior y los actualiza
            overlapped_drones = self.dron_solapado.get((old_y, old_x), [])
            if id in overlapped_drones:
                overlapped_drones.remove(id)
                if overlapped_drones:
                    # Coloca el siguiente dron en la lista si hay alguno
                    next_drone_id = overlapped_drones[0]
                    # Obtiene la información del siguiente dron
                    next_drone_color = self.drones_positions[next_drone_id][2]
                    # Coloca el siguiente dron en la posición anterior
                    self.place_drone(old_x, old_y, next_drone_id, next_drone_color)
                    #
                    self.dron_solapado[(old_y, old_x)] = overlapped_drones
                else:
                    # Si no hay más drones, elimina la entrada del diccionario y limpia la posición
                    self.dron_solapado.pop((old_y, old_x), None)
                    self.grid[old_y][old_x] = '  '  # Limpia con espacios de ancho fijo

        # Mueve el dron a la nueva posición
        overlapped_drones = self.dron_solapado.get((new_y, new_x), [])
        # Verifica si hay otros drones en la nueva posición
        if overlapped_drones:
            # Si ya hay drones en la posición, agrega el dron a la lista y coloca el nuevo dron con color de solapamiento
            overlapped_drones.append(id)
            self.dron_solapado[(new_y, new_x)] = overlapped_drones
            self.place_drone(new_x, new_y, id, "amarillo")  # Usa el color amarillo para indicar solapamiento
        else:
            # Si no hay drones, coloca el dron y actualiza las posiciones
            self.dron_solapado[(new_y, new_x)] = [id]
            self.place_drone(new_x, new_y, id, color)

        # Actualiza el diccionario de posiciones de drones con la nueva posición y color
        self.drones_positions[id] = (new_x, new_y, color)
