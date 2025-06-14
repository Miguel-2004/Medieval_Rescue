# Importamos las clases que se requieren para manejar los agentes (Agent) y su entorno (Model).
from mesa import Agent, Model

# Debido a que necesitamos que existe un solo agente por celda, elegimos ''SingleGrid''.
from mesa.space import SingleGrid, MultiGrid

# Con ''RandomActivation'', hacemos que todos los agentes se activen ''al mismo tiempo''.
from mesa.time import RandomActivation

# Haremos uso de ''batch_run'' para ejecutar varias simulaciones
from mesa.batchrunner import batch_run

# seaborn lo usaremos desplegar una gráficas más ''vistosas'' de nuestro modelo
from functools import partial

# Haremos uso de ''DataCollector'' para obtener información de cada paso de la simulación.
from mesa.datacollection import DataCollector

# matplotlib lo usaremos crear una animación de cada uno de los pasos del modelo.
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
plt.rcParams["animation.html"] = "jshtml"
matplotlib.rcParams['animation.embed_limit'] = 2**128

# Importamos los siguientes paquetes para el mejor manejo de valores numéricos.
import numpy as np
import pandas as pd

# Definimos otros paquetes que vamos a usar para medir el tiempo de ejecución de nuestro algoritmo.
import time
import datetime
import random

import heapq
from typing import List, Tuple, Dict

import json

class FireFighter(Agent):
    def __init__(self, id, model, x, y):
        # Llamar al constructor de la clase padre para inicializar id y model
        super().__init__(model)

        # Establecer el nivel de energía inicial para el bombero
        self.energy = 4

        # Booleano que indica si el bombero está cargando algo actualmente
        self.carrying = False

        # Lista para almacenar la ruta que tomará el bombero
        self.path = []

        # Lista para almacenar los movimientos requeridos para alcanzar el objetivo
        self.movesToGoal = []

        # Almacenar la posición anterior del bombero
        self.previousPos = self.pos

        # Marcador de posición para la siguiente posición del bombero
        self.nextPos = None

        # Almacenar el Punto de Interés (POI) más cercano
        self.nearestPOI = None

        # Almacenar el punto de entrada más cercano para el bombero
        self.nearestEntrypoint = None

        # Booleano que indica si el bombero está bloqueado y no puede moverse
        self.isBlocked = False

        # Booleano que indica si el bombero puede avanzar hacia su objetivo
        self.canAdvance = True

        # Costo de moverse a la siguiente posición
        self.moveCost = 1

        # Índice para rastrear el movimiento actual en una secuencia de movimientos
        self.move_index = 1

        # Establecer la posición inicial del bombero como una tupla (x, y)
        self.initialPos = (x, y)


    def calculateNearest(self):
        # Calcular el Punto de Interés (POI) más cercano a la casilla actual del bombero
        current_tile = [obj for obj in self.model.grid.get_cell_list_contents([self.pos]) if isinstance(obj, Tile)][0]

        # Si no está cargando nada y hay POIs disponibles, calcular el POI más cercano
        if self.carrying == False and len(self.model.POIsPositions) > 0:
            distances = {poi: abs(poi[0] - current_tile.pos[0]) + abs(poi[1]-current_tile.pos[1]) for poi in self.model.POIsPositions}
            # Encontrar el POI más cercano basado en las distancias calculadas
            self.nearestPOI = min(distances, key=distances.get)

        # Si está cargando algo, calcular el punto de entrada más cercano
        elif self.carrying == True:
            distances = {entrypoint: abs(entrypoint[0] - current_tile.pos[0]) + abs(entrypoint[1]-current_tile.pos[1]) for entrypoint in self.model.entryPoints}
            # Encontrar el punto de entrada más cercano basado en las distancias calculadas
            self.nearestEntrypoint = min(distances, key=distances.get)


    def dijkstraToNearest(self, graph: Dict[Tuple[int, int], Dict[Tuple[int, int], int]],
                            start: Tuple[int, int],
                            poi: Tuple[int, int]) -> Tuple[List[Tuple[int, int]], int,]:
        # Inicializar una lista vacía para almacenar los movimientos hacia el objetivo
        self.movesToGoal = []

        # Inicializar una lista vacía para almacenar la ruta tomada para alcanzar el POI
        path = []

        # Crear un diccionario para mantener la distancia más corta a cada nodo, inicializada a infinito
        distances = {node: float('infinity') for node in graph}

        # Establecer la distancia al nodo inicial a 0
        distances[start] = 0

        # Crear una cola de prioridad inicializada con el nodo inicial
        pq = [(0, start)]

        # Diccionario para mantener el registro del nodo anterior para cada nodo
        previous = {}

        # Mientras haya nodos en la cola de prioridad
        while pq:
            # Obtener el nodo con la distancia más pequeña
            current_distance, current_node = heapq.heappop(pq)

            # Si el nodo actual es el POI, reconstruir la ruta
            if current_node == poi:
                while current_node in previous:
                    path.append(current_node)  # Agregar el nodo actual a la ruta
                    current_node = previous[current_node]  # Moverse al nodo anterior
                path.append(start)  # Agregar el nodo inicial a la ruta
                path = list(reversed(path))  # Revertir la ruta para obtener el orden correcto

                break  # Salir del bucle una vez que se alcance el POI

            # Si la distancia actual es mayor que la distancia registrada, omitir el procesamiento
            if current_distance > distances[current_node]:
                continue

            # Verificar cada vecino del nodo actual
            for neighbor, weight in graph[current_node].items():
                distance = current_distance + weight  # Calcular la distancia al vecino
                # Si la distancia calculada es menor que la distancia registrada, actualizarla
                if distance < distances[neighbor]:
                    distances[neighbor] = distance  # Actualizar la distancia más corta
                    previous[neighbor] = current_node  # Actualizar el nodo anterior
                    heapq.heappush(pq, (distance, neighbor))  # Agregar el vecino a la cola de prioridad

        # Almacenar la ruta calculada en movesToGoal
        self.movesToGoal = path

    def move(self, next_position):
        # Posición actual del agente
        current_position = self.pos

        # Obtener la Casilla actual
        current_tile = [obj for obj in self.model.grid.get_cell_list_contents([current_position]) if isinstance(obj, Tile)][0]

        # Remover el bombero de la lista de bomberos de la casilla actual
        current_tile.hasFireFighter.remove(self)

        # Obtener la siguiente Casilla
        next_tile = [obj for obj in self.model.grid.get_cell_list_contents([next_position]) if isinstance(obj, Tile)][0]

        # Agregar el bombero a la lista de bomberos de la siguiente casilla
        next_tile.hasFireFighter.append(self)

        # Mover el agente a la siguiente posición en la cuadrícula
        self.model.grid.move_agent(self, next_position)

        # Calcular el cambio en la posición (dx y dy)
        dx = next_position[0] - current_position[0]
        dy = next_position[1] - current_position[1]

        # Agregar la información de la casilla afectada al modelo
        self.model.appendAffectedTile(current_tile, "move", dx, dy)

        # Reducir energía basándose en si el bombero está cargando una víctima o no
        if self.carrying:
            self.energy -= 2  # Cuesta más energía si está cargando una víctima
        else:
            self.energy -= 1  # Costo estándar de movimiento

        # Si hay un POI (Punto de Interés) en la nueva posición, revelarlo
        if next_tile.hasPOI == True:
            next_tile.hasPOI = False  # Marcar el POI como revelado
            self.model.numOfPOIs -= 1  # Disminuir el recuento de POIs

            # Si el tipo de POI es una víctima, aumentar el número de víctimas
            if next_tile.poi == "v":
                next_tile.numberOfVictims += 1  # Incrementar el número de víctimas
                self.carryVictim()  # Llamar función para cargar la víctima

            next_tile.poi = None  # Limpiar la información del POI
            self.model.currentPOIS -= 1  # Disminuir el recuento de POIs actuales

        # Agregar la información de la casilla afectada para la siguiente casilla
        self.model.appendAffectedTile(next_tile, "stand", dx, dy)

        # Limpiar la lista de casillas afectadas para la siguiente acción
        self.model.affectedTiles = []


    def step(self):
        # Reiniciar el índice de movimiento al primer movimiento
        self.move_index = 1

        # Reponer Puntos de Interés (POIs) en el modelo
        self.model.replenishPOIs()

        # Determinar el objetivo más cercano basándose en si el bombero está cargando una víctima o no
        if self.carrying == False:
            self.calculateNearest()  # Calcular el POI más cercano
            self.dijkstraToNearest(self.model.graph, self.pos, self.nearestPOI)  # Encontrar la ruta al POI más cercano
            goalPos = self.nearestPOI  # Establecer la posición objetivo al POI más cercano
        else:
            self.calculateNearest()  # Calcular el punto de entrada más cercano
            self.dijkstraToNearest(self.model.graph, self.pos, self.nearestEntrypoint)  # Encontrar la ruta al punto de entrada más cercano
            goalPos = self.nearestEntrypoint  # Establecer la posición objetivo al punto de entrada más cercano

        # Continuar moviéndose mientras haya energía y el índice de movimiento esté dentro de los límites de movesToGoal
        while self.energy > 0 and self.move_index < len(self.movesToGoal) and self.canAdvance == True:
            # Si está en el POI más cercano, encontrar el punto de entrada más cercano
            if self.pos == self.nearestPOI:
                self.move_index = 1  # Reiniciar índice de movimiento
                self.calculateNearest()  # Calcular el punto de entrada más cercano
                self.dijkstraToNearest(self.model.graph, self.pos, self.nearestEntrypoint)  # Encontrar la ruta al punto de entrada más cercano
                goalPos = self.nearestEntrypoint  # Actualizar posición objetivo al punto de entrada más cercano
            # Si está en el punto de entrada más cercano, soltar la víctima y encontrar el POI más cercano
            elif self.pos == self.nearestEntrypoint:
                self.move_index = 1  # Reiniciar índice de movimiento
                self.dropVictim()  # Soltar la víctima en el punto de entrada
                self.calculateNearest()  # Calcular el POI más cercano
                self.dijkstraToNearest(self.model.graph, self.pos, self.nearestPOI)  # Encontrar la ruta al POI más cercano
                goalPos = self.nearestPOI  # Actualizar posición objetivo al POI más cercano

            # Obtener el siguiente movimiento de la lista de movimientos hacia el objetivo
            move = self.movesToGoal[self.move_index]

            # Obtener las casillas actual y siguiente
            current_tile = [obj for obj in self.model.grid.get_cell_list_contents([self.pos]) if isinstance(obj, Tile)][0]
            next_tile = [obj for obj in self.model.grid.get_cell_list_contents([move]) if isinstance(obj, Tile)][0]

            # Evaluar si hay algún bloqueo entre la posición actual y la siguiente posición
            match self.model.graph[self.pos][move]:
                case 1:
                    self.isBlocked = False  # No hay bloqueo
                case 2:
                    self.isBlocked = True  # Bloqueado por una puerta
                    blocker = "Door"
                case 3:
                    self.isBlocked = True  # Bloqueado por una pared dañada
                    blocker = "Damaged Wall"
                case 5:
                    self.isBlocked = True  # Bloqueado por una pared
                    blocker = "Wall"

            # Si no está bloqueado y puede avanzar, proceder con el movimiento o acción
            if self.isBlocked == False and self.canAdvance:
                if next_tile.fireStatus == 2:  # Si la siguiente casilla está en llamas
                    if self.energy >= 2:  # Verificar si hay suficiente energía para extinguir
                        self.extinguish(move)  # Extinguir el fuego en la siguiente posición
                    else:
                        self.canAdvance = False  # No puede avanzar debido a energía insuficiente
                else:
                    if self.energy >= self.moveCost:  # Verificar si hay suficiente energía para moverse
                        self.move(move)  # Moverse a la siguiente posición
                        self.move_index += 1  # Incrementar índice de movimiento
                    else:
                        self.canAdvance = False  # No puede avanzar debido a energía insuficiente
            # Si está bloqueado, manejar el tipo de bloqueo
            elif self.isBlocked == True and self.canAdvance:
                match blocker:
                    case "Door":
                        if self.energy >= 1:  # Verificar energía para manipular la puerta
                            self.manipulateDoor(True, move)  # Manipular puerta para pasar
                            self.model.graph[self.pos][move] = 1  # Actualizar grafo para reflejar movimiento
                            self.model.graph[move][self.pos] = 1  # Actualizar grafo inverso
                        else:
                            self.canAdvance = False  # No puede avanzar debido a energía insuficiente
                    case "Damaged Wall":
                        if self.energy >= 2:  # Verificar energía para dañar la pared
                            self.damage(False, move)  # Dañar la pared para pasar
                            self.model.graph[self.pos][move] = 1  # Actualizar grafo para reflejar movimiento
                            self.model.graph[move][self.pos] = 1  # Actualizar grafo inverso
                        else:
                            self.canAdvance = False  # No puede avanzar debido a energía insuficiente
                    case "Wall":
                        if self.energy >= 4:  # Verificar energía para dañar la pared
                            self.damage(True, move)  # Dañar la pared para pasar
                            self.model.graph[self.pos][move] = 1  # Actualizar grafo para reflejar movimiento
                            self.model.graph[move][self.pos] = 1  # Actualizar grafo inverso
                        else:
                            self.canAdvance = False  # No puede avanzar debido a energía insuficiente

            # Si está en el POI más cercano, encontrar el punto de entrada más cercano
            if self.pos == self.nearestPOI:
                self.move_index = 1  # Reiniciar índice de movimiento
                self.calculateNearest()  # Calcular el punto de entrada más cercano
                self.dijkstraToNearest(self.model.graph, self.pos, self.nearestEntrypoint)  # Encontrar la ruta al punto de entrada más cercano
                goalPos = self.nearestEntrypoint  # Actualizar posición objetivo al punto de entrada más cercano
            # Si está en el punto de entrada más cercano, soltar la víctima y encontrar el POI más cercano
            elif self.pos == self.nearestEntrypoint:
                self.move_index = 1  # Reiniciar índice de movimiento
                self.dropVictim()  # Soltar la víctima en el punto de entrada
                self.calculateNearest()  # Calcular el POI más cercano
                self.dijkstraToNearest(self.model.graph, self.pos, self.nearestPOI)  # Encontrar la ruta al POI más cercano
                goalPos = self.nearestPOI  # Actualizar posición objetivo al POI más cercano

        # Si está en el POI más cercano, reiniciar índice de movimiento
        if self.pos == self.nearestPOI:
            self.move_index = 1

        # Si está en el punto de entrada más cercano, reiniciar índice de movimiento y soltar la víctima
        if self.pos == self.nearestEntrypoint:
            self.move_index = 1
            self.dropVictim()  # Soltar la víctima en el punto de entrada

        # Si la energía se agotó, reiniciar índice de movimiento
        if self.energy <= 0:
            self.move_index = 1

        # Reiniciar el nivel de energía para el siguiente turno
        self.energy = 4 + self.energy  # Restaurar energía
        if self.energy > 8:  # Limitar la energía a 8
            self.energy = 8

        self.canAdvance = True  # Reiniciar la capacidad de avanzar
        self.model.throwDice()  # Ejecutar lanzamiento de dados para cualquier mecánica del juego

        # Actualizar el diccionario de agentes actuales con el estado actual del agente
        self.model.currentAgentsDictionary[self.unique_id] = self.model.allTiles

        # Limpiar la lista de todas las casillas para el siguiente turno
        self.model.allTiles = []

    def manipulateDoor(self, status, next_pos): # True para cerrar puerta, false para abrirla
        # Obtener la casilla actual donde se encuentra el agente
        current_tile = [obj for obj in self.model.grid.get_cell_list_contents([self.pos]) if isinstance(obj, Tile)][0]

        # Obtener la casilla en la dirección de la siguiente posición
        tile2 = [obj for obj in self.model.grid.get_cell_list_contents([next_pos]) if isinstance(obj, Tile)][0]

        # Establecer el estado de la puerta (abierta/cerrada) tanto para la casilla actual como para la siguiente
        current_tile.wall.isOpen = status
        tile2.wall.isOpen = status

        # Calcular el cambio en la posición
        dx = next_pos[0] - self.pos[0]
        dy = next_pos[1] - self.pos[1]

        # Disminuir energía por la acción de manipular la puerta
        self.energy -= 1

        # Agregar las casillas afectadas al modelo para seguimiento
        self.model.appendAffectedTile(current_tile,"stand", dx, dy)
        self.model.appendAffectedTile(tile2,"stand", dx, dy)

        # Limpiar la lista de casillas afectadas para la siguiente operación
        self.model.affectedTiles = []

    def extinguish(self, move):
        # Obtener la casilla actual donde se encuentra el agente
        current_tile = [obj for obj in self.model.grid.get_cell_list_contents([self.pos]) if isinstance(obj, Tile)][0]

        # Obtener la casilla en la dirección del movimiento
        next_tile = [obj for obj in self.model.grid.get_cell_list_contents([move]) if isinstance(obj, Tile)][0]

        # Establecer el estado de fuego de la siguiente casilla a 0 (extinguido)
        next_tile.fireStatus = 0

        # Disminuir energía por la acción de extinguir el fuego
        self.energy -= 2

        # Calcular el cambio en la posición
        dx = move[0] - self.pos[0]
        dy = move[1] - self.pos[1]

        # Agregar la casilla afectada al modelo para seguimiento
        self.model.appendAffectedTile(next_tile,"stand", dx, dy)


    def damage(self, demolish, next_pos):
        # Obtener la casilla actual donde se encuentra el agente
        current_tile = [obj for obj in self.model.grid.get_cell_list_contents([self.pos]) if isinstance(obj, Tile)][0]

        # Calcular el cambio en la posición
        dx = next_pos[0] - self.pos[0]
        dy = next_pos[1] - self.pos[1]

        # Obtener la casilla en la dirección de la siguiente posición
        other_tile = [obj for obj in self.model.grid.get_cell_list_contents([(self.pos[0]+dx, self.pos[1]+dy)]) if isinstance(obj, Tile)][0]

        if demolish:
            # Disminuir energía por la acción de demoler
            self.energy -= 4
            self.model.damageCounter += 2

            # Manejar el caso para diferentes direcciones de demolición
            if dx == -1:  # Moviéndose hacia la izquierda
                other_tile.wall.bottomHealth = 0
                other_tile.wall.bottom = 0
                current_tile.wall.topHealth = 0
                current_tile.wall.top = 0
            elif dy == -1:  # Moviéndose hacia arriba
                other_tile.wall.rightHealth = 0
                other_tile.wall.right = 0
                current_tile.wall.leftHealth = 0
                current_tile.wall.left = 0
            elif dx == 1:  # Moviéndose hacia la derecha
                other_tile.wall.topHealth = 0
                other_tile.wall.top = 0
                current_tile.wall.bottomHealth = 0
                current_tile.wall.bottom = 0
            elif dy == 1:  # Moviéndose hacia abajo
                other_tile.wall.leftHealth = 0
                other_tile.wall.left = 0
                current_tile.wall.rightHealth = 0
                current_tile.wall.right = 0
        else:
            # Disminuir energía por la acción de dañar
            self.energy -= 2
            self.model.damageCounter += 1

            # Manejar el caso para diferentes direcciones de daño
            if dx == -1:  # Moviéndose hacia la izquierda
                other_tile.wall.bottomHealth -= 2
                if other_tile.wall.bottomHealth <= 0:  # Verificar si la pared está destruida
                    other_tile.wall.bottom = 0
                current_tile.wall.topHealth -= 2
                if current_tile.wall.topHealth <= 0:  # Verificar si la pared está destruida
                    current_tile.wall.top = 0
            elif dy == -1:  # Moviéndose hacia arriba
                other_tile.wall.rightHealth -= 2
                if other_tile.wall.rightHealth <= 0:  # Verificar si la pared está destruida
                    other_tile.wall.right = 0
                current_tile.wall.leftHealth -= 2
                if current_tile.wall.leftHealth <= 0:  # Verificar si la pared está destruida
                    current_tile.wall.left = 0
            elif dx == 1:  # Moviéndose hacia la derecha
                other_tile.wall.topHealth -= 2
                if other_tile.wall.topHealth <= 0:  # Verificar si la pared está destruida
                    other_tile.wall.top = 0
                current_tile.wall.bottomHealth -= 2
                if current_tile.wall.bottomHealth <= 0:  # Verificar si la pared está destruida
                    current_tile.wall.bottom = 0
            elif dy == 1:  # Moviéndose hacia abajo
                other_tile.wall.leftHealth -= 2
                if other_tile.wall.leftHealth <= 0:  # Verificar si la pared está destruida
                    other_tile.wall.left = 0
                current_tile.wall.rightHealth -= 2
                if current_tile.wall.rightHealth <= 0:  # Verificar si la pared está destruida
                    current_tile.wall.right = 0

        # Agregar las casillas afectadas al modelo para seguimiento
        self.model.appendAffectedTile(current_tile,"stand", dx, dy)
        self.model.appendAffectedTile(other_tile,"stand", dx, dy)

        # Limpiar la lista de casillas afectadas para la siguiente operación
        self.model.affectedTiles = []


    def carryVictim(self):
        # Obtener la casilla actual donde se encuentra el agente
        current_tile = [obj for obj in self.model.grid.get_cell_list_contents([self.pos]) if isinstance(obj, Tile)][0]

        # Verificar si hay víctimas para cargar en la casilla actual
        if current_tile.numberOfVictims > 0:
            # Establecer el estado de carga a True
            self.carrying = True
            # Disminuir el número de víctimas en la casilla actual
            current_tile.numberOfVictims -= 1
            # Establecer el costo de movimiento a 2 mientras carga una víctima
            self.moveCost = 2


    def dropVictim(self):
        # Obtener la casilla actual donde se encuentra el agente
        current_tile = [obj for obj in self.model.grid.get_cell_list_contents([self.pos]) if isinstance(obj, Tile)][0]

        # Establecer el estado de carga a False
        self.carrying = False
        # Reiniciar el costo de movimiento a 1 después de soltar la víctima
        self.moveCost = 1
        # Incrementar el conteo de víctimas salvadas en el modelo
        self.model.savedVictims += 1

        # Agregar la casilla actual como afectada por la acción de soltar la víctima
        self.model.appendAffectedTile(current_tile,"stand", 0, 0)

class Wall():
    def __init__(self, id, top, left, bottom, right, isDoor=0, isOpen=False):
        # Asignar un identificador único a la pared
        self.unique_id = id

        # Establecer las propiedades de la pared para cada lado (arriba, abajo, izquierda, derecha)
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right

        # Especificar si la pared tiene una puerta (0 indica que no hay puerta)
        self.isDoor = isDoor

        # Booleano que indica si la puerta está actualmente abierta
        self.isOpen = isOpen

        # Inicializar la salud de las paredes (4 veces el valor de presencia de la pared)
        self.topHealth = 4 * top
        self.bottomHealth = 4 * bottom
        self.leftHealth = 4 * left
        self.rightHealth = 4 * right

        # Ajustar las propiedades de la pared si hay una puerta presente
        if self.isDoor != 0:
            if self.isDoor == 1:  # Puerta en la parte superior
                self.top = 2  # Cambiar pared superior para representar una puerta
                self.topHealth = 2  # Establecer salud para la puerta
            if self.isDoor == 2:  # Puerta en la izquierda
                self.left = 2  # Cambiar pared izquierda para representar una puerta
                self.leftHealth = 2  # Establecer salud para la puerta
            if self.isDoor == 3:  # Puerta en la parte inferior
                self.bottom = 2  # Cambiar pared inferior para representar una puerta
                self.bottomHealth = 2  # Establecer salud para la puerta
            if self.isDoor == 4:  # Puerta en la derecha
                self.right = 2  # Cambiar pared derecha para representar una puerta
                self.rightHealth = 2  # Establecer salud para la puerta

class Tile():
    def __init__(self, id, top, left, bottom, right, isDoor, isOpen=False):
        # Asignar un identificador único a la casilla
        self.unique_id = id

        # Inicializar la posición de la casilla (por defecto es None)
        self.pos = None

        # Crear un objeto Wall para la casilla con las propiedades de pared proporcionadas
        self.wall = Wall(id, top, left, bottom, right, isDoor, isOpen)

        # Inicializar el estado de fuego de la casilla (0 indica que no hay fuego)
        self.fireStatus = 0

        # Booleano que indica si la casilla tiene un Punto de Interés (POI)
        self.hasPOI = False

        # Contador para el número de víctimas presentes en la casilla
        self.numberOfVictims = 0

        # Lista para contener bomberos asignados a la casilla
        self.hasFireFighter = []

        # Referencia a un POI (Punto de Interés) asociado con la casilla
        self.poi = None

class FireRescueModel(Model):
    def __init__(self, firefighters, width, height, entrypoints, walls, doors, fires, pois):
        super().__init__()  # Inicializar la clase padre Model
        self.grid = MultiGrid(width, height, torus=False)  # Crear una cuadrícula para el modelo
        self.schedule = RandomActivation(self)  # Crear un programador para los agentes

        self.steps = 0  # Contador para el número de pasos dados en la simulación
        self.entryPoints = entrypoints  # Almacenar los puntos de entrada para los bomberos
        self.damageCounter = 0  # Contador para rastrear el daño
        self.numOfPOIs = 15  # Número total de Puntos de Interés
        self.truePOIs = 10  # Número de Puntos de Interés verdaderos
        self.falsePOIs = 5  # Número de Puntos de Interés falsos
        self.currentPOIS = 0  # Contador para Puntos de Interés actualmente activos
        self.savedVictims = 0  # Contador para víctimas salvadas
        self.deadVictims = 0  # Contador para víctimas muertas
        self.running = True  # Bandera para indicar si la simulación está corriendo
        self.POIsPositions = []  # Lista para almacenar las posiciones de los Puntos de Interés
        self.dictionaryList = []  # Lista para almacenar diccionarios relacionados con la simulación
        self.tilesMatrix = {}  # Diccionario para mantener el estado de las casillas
        self.initialDictionary = {}  # Diccionario para condiciones iniciales
        self.currentAgentsDictionary = {}  # Diccionario para los agentes actuales
        self.walls = walls  # Almacenar configuraciones de paredes
        self.doors = doors  # Almacenar configuraciones de puertas
        self.win = 0  # Contador para condiciones de victoria
        self.demolishedLose = 0  # Contador para pérdidas debido a demolición
        self.deadVictimLose = 0  # Contador para pérdidas debido a víctimas muertas
        self.affectedTiles = []  # Lista para almacenar casillas afectadas durante la simulación
        self.allTiles = []  # Lista para almacenar todas las casillas

        self.graph = self.generateGraph(walls)  # Generar una representación gráfica de las paredes
        self.graph = self.addDoorArches(self.graph, doors, cost=2)  # Agregar arcos de puertas al grafo con un costo

        # Colocar las casillas (cuadrantes) en la cuadrícula
        for j, row in enumerate(walls):
            for i, wall in enumerate(row):
                entryPointTile = False  # Bandera para verificar si la casilla es un punto de entrada
                for point in entrypoints:
                    if point[0] == j+1 and point[1] == i+1:  # Verificar si el cuadrante colocado tiene un punto de entrada
                        if point[0] == 1:  # Punto de entrada superior
                            tile = Tile((j+1,i+1), wall[0], wall[1], wall[2], wall[3], 1, True)
                            entryPointTile = True
                        elif point[1] == 1:  # Punto de entrada izquierdo
                            tile = Tile((j+1,i+1), wall[0], wall[1], wall[2], wall[3], 2, True)
                            entryPointTile = True
                        elif point[0] == 6:  # Punto de entrada inferior
                            tile = Tile((j+1,i+1), wall[0], wall[1], wall[2], wall[3], 3, True)
                            entryPointTile = True
                        elif point[1] == 8:  # Punto de entrada derecho
                            tile = Tile((j+1,i+1), wall[0], wall[1], wall[2], wall[3], 4, True)
                            entryPointTile = True

                if not entryPointTile:
                    tile = Tile((j+1,i+1), wall[0], wall[1], wall[2], wall[3], 0)  # Crear una casilla normal si no hay punto de entrada

                self.grid.place_agent(tile, (j+1, i+1))  # Colocar la casilla en la cuadrícula

        # Colocar fuegos en la cuadrícula
        for fire in fires:
            tile = [obj for obj in self.grid.get_cell_list_contents([(fire[0], fire[1])]) if isinstance(obj, Tile)][0]
            tile.fireStatus = 2  # Establecer el estado de fuego de la casilla

        # Colocar puertas en la cuadrícula
        for door in doors:
            x1, y1, x2, y2 = door

            tile1 = [obj for obj in self.grid.get_cell_list_contents([(x1, y1)]) if isinstance(obj, Tile)][0]
            tile2 = [obj for obj in self.grid.get_cell_list_contents([(x2, y2)]) if isinstance(obj, Tile)][0]

            dx = abs(x1 - x2)  # Calcular distancia horizontal entre casillas de puerta
            dy = abs(y1 - y2)  # Calcular distancia vertical entre casillas de puerta

            if dx == 0 and dy == 1:
                # Las casillas están una al lado de la otra horizontalmente
                if y1 < y2:
                    tile1.wall.right = 2  # Establecer pared derecha de tile1 como puerta
                    tile2.wall.left = 2  # Establecer pared izquierda de tile2 como puerta
                    tile1.wall.isDoor = 4  # Marcar pared de tile1 como puerta
                    tile2.wall.isDoor = 2  # Marcar pared de tile2 como puerta
                    tile1.wall.rightHealth = 2  # Establecer salud de pared derecha
                    tile2.wall.leftHealth = 2  # Establecer salud de pared izquierda
                else:
                    tile1.wall.left = 2  # Establecer pared izquierda de tile1 como puerta
                    tile2.wall.right = 2  # Establecer pared derecha de tile2 como puerta
                    tile1.wall.isDoor = 2  # Marcar pared de tile1 como puerta
                    tile2.wall.isDoor = 4  # Marcar pared de tile2 como puerta
                    tile1.wall.leftHealth = 2  # Establecer salud de pared izquierda
                    tile2.wall.rightHealth = 2  # Establecer salud de pared derecha

            elif dy == 0 and dx == 1:
                # Las casillas están una encima de la otra verticalmente
                if x1 < x2:
                    tile1.wall.bottom = 2  # Establecer pared inferior de tile1 como puerta
                    tile2.wall.top = 2  # Establecer pared superior de tile2 como puerta
                    tile1.wall.isDoor = 3  # Marcar pared de tile1 como puerta
                    tile2.wall.isDoor = 1  # Marcar pared de tile2 como puerta
                    tile1.wall.bottomHealth = 2  # Establecer salud de pared inferior
                    tile2.wall.topHealth = 2  # Establecer salud de pared superior
                else:
                    tile1.wall.top = 2  # Establecer pared superior de tile1 como puerta
                    tile2.wall.bottom = 2  # Establecer pared inferior de tile2 como puerta
                    tile1.wall.isDoor = 1  # Marcar pared de tile1 como puerta
                    tile2.wall.isDoor = 3  # Marcar pared de tile2 como puerta
                    tile1.wall.topHealth = 2  # Establecer salud de pared superior
                    tile2.wall.bottomHealth = 2  # Establecer salud de pared inferior

        # Colocar bomberos fuera de la casa en los puntos de entrada
        for i in range(firefighters):
            x, y = random.choice(entryPoints)  # Seleccionar aleatoriamente un punto de entrada
            tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]

            firefighter = FireFighter(i, self, x, y)  # Crear un agente bombero
            tile.hasFireFighter.append(firefighter)  # Agregar el bombero a la casilla
            self.grid.place_agent(firefighter, (x, y))  # Colocar el bombero en la cuadrícula
            self.schedule.add(firefighter)  # Agregar el bombero al programador

        # Colocar Puntos de Interés (POIs) en la cuadrícula
        for poi in pois:
            x, y, victim = poi  # Desempaquetar los datos del POI
            tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]
            self.spawnPOI(x, y, tile, victim)  # Generar el POI en la cuadrícula
            self.affectedTiles = []  # Reiniciar lista de casillas afectadas

        # Inicializar el tilesMatrix con estados de paredes
        for i in range(1, self.grid.width-1):
            for j in range(1, self.grid.height-1):
                tile = [obj for obj in self.grid.get_cell_list_contents([(i, j)]) if isinstance(obj, Tile)][0]
                self.tilesMatrix[(i, j)] = [tile.wall.top, tile.wall.left, tile.wall.bottom, tile.wall.right]  # Almacenar estados de paredes en la matriz

        self.datacollector = DataCollector(
            model_reporters={"Match": lambda m: self.get_grid_state()}
        )

    def get_grid_state(self):
        grid_state = {}
        for i in range(1, self.grid.width-1):
            for j in range(1, self.grid.height-1):
                tile = [obj for obj in self.grid.get_cell_list_contents([(i, j)]) if isinstance(obj, Tile)][0]
                grid_state[(i, j)] = tile.fireStatus
        return grid_state

    def appendAffectedTile(self, tile, stateString, dx, dy):
        firefightersIDs = []  # Inicializar una lista para almacenar los IDs únicos de los bomberos en la casilla
        for firefighter in tile.hasFireFighter:
            firefightersIDs.append(firefighter.unique_id)  # Agregar cada ID único de bombero a la lista

        # Agregar el estado de la casilla e información relevante a la lista affectedTiles
        self.affectedTiles.append([tile.pos,  # Posición de la casilla
                                  tile.wall.top,  # Estado de la pared superior
                                  tile.wall.left,  # Estado de la pared izquierda
                                  tile.wall.bottom,  # Estado de la pared inferior
                                  tile.wall.right,  # Estado de la pared derecha
                                  tile.wall.isOpen,  # Si la pared está abierta
                                  tile.wall.topHealth,  # Salud de la pared superior
                                  tile.wall.leftHealth,  # Salud de la pared izquierda
                                  tile.wall.bottomHealth,  # Salud de la pared inferior
                                  tile.wall.rightHealth,  # Salud de la pared derecha
                                  tile.fireStatus,  # Estado de fuego de la casilla
                                  tile.hasPOI,  # Si la casilla tiene un Punto de Interés
                                  tile.numberOfVictims,  # Número de víctimas en la casilla
                                  firefightersIDs,  # Lista de IDs de bomberos
                                  stateString,  # Cadena de estado para información adicional
                                  dx,  # Cambio en posición x
                                  dy, # Cambio en posición y
                                  self.damageCounter,  # Daño de la casa
                                  tile.poi,  # POI de la casa
                                  self.savedVictims,  # Víctimas salvadas
                                  self.deadVictims])  # Víctimas muertas

        # Agregar el mismo estado de la casilla e información relevante a la lista allTiles
        self.allTiles.append([tile.pos,  # Posición de la casilla
                                  tile.wall.top,  # Estado de la pared superior
                                  tile.wall.left,  # Estado de la pared izquierda
                                  tile.wall.bottom,  # Estado de la pared inferior
                                  tile.wall.right,  # Estado de la pared derecha
                                  tile.wall.isOpen,  # Si la pared está abierta
                                  tile.wall.topHealth,  # Salud de la pared superior
                                  tile.wall.leftHealth,  # Salud de la pared izquierda
                                  tile.wall.bottomHealth,  # Salud de la pared inferior
                                  tile.wall.rightHealth,  # Salud de la pared derecha
                                  tile.fireStatus,  # Estado de fuego de la casilla
                                  tile.hasPOI,  # Si la casilla tiene un Punto de Interés
                                  tile.numberOfVictims,  # Número de víctimas en la casilla
                                  firefightersIDs,  # Lista de IDs de bomberos
                                  stateString,  # Cadena de estado para información adicional
                                  dx,  # Cambio en posición x
                                  dy,  # Cambio en posición y
                                  self.damageCounter,  # Daño de la casa
                                  tile.poi,  # POI de la casa
                                  self.savedVictims,  # Víctimas salvadas
                                  self.deadVictims])  # Víctimas muertas


    def revealPOI(self, current_tile):
        # Si la casilla con fuego tiene un Punto de Interés (POI), revelarlo y matar la víctima si está presente
        if current_tile.hasPOI == True:

            current_tile.hasPOI = False  # Marcar el POI como revelado
            self.numOfPOIs -= 1  # Disminuir el número total de POIs
            self.currentPOIS -= 1  # Disminuir el número actual de POIs
            if current_tile.poi == "v":  # Verificar si el POI representa una víctima

                current_tile.numberOfVictims -= 1  # Disminuir el número de víctimas en la casilla
                self.deadVictims += 1  # Aumentar el conteo de víctimas muertas
                current_tile.poi = None  # Remover el POI de la casilla


    def spawnPOI(self, x, y, tile, victim):
        # Si el POI aterriza en un agente bombero...
        # revelarlo y disminuir el número de POIs
        while len(tile.hasFireFighter) > 0:
            tile.hasPOI = False  # Marcar el POI como revelado
            self.numOfPOIs -= 1  # Disminuir el número total de POIs
            if victim == "v":  # Verificar si la víctima está presente
                tile.numberOfVictims += 1  # Aumentar el número de víctimas en la casilla

            # Colocar otro POI en una posición aleatoria
            x = self.random.randint(1, self.grid.width - 2)  # Obtener una coordenada x aleatoria
            y = self.random.randint(1, self.grid.height - 2)  # Obtener una coordenada y aleatoria
            tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]  # Obtener la casilla en la nueva posición

        # Si el POI aterriza en otro POI...
        # disminuir el número de POIs
        while tile.hasPOI == True:
            # Colocar otro POI en una posición aleatoria
            x = self.random.randint(1, self.grid.width - 2)  # Obtener una coordenada x aleatoria
            y = self.random.randint(1, self.grid.height - 2)  # Obtener una coordenada y aleatoria
            tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]  # Obtener la casilla en la nueva posición

        self.POIsPositions.append(tile.pos)  # Agregar la posición de la casilla a la lista de posiciones POI
        # Colocar el POI
        tile.hasPOI = True  # Marcar la casilla como que tiene un POI
        tile.poi = victim  # Establecer el tipo de POI (víctima o no)
        self.currentPOIS += 1  # Aumentar el número actual de POIs
        # Apagar fuegos o humo
        if tile.fireStatus != 0:
            tile.fireStatus = 0  # Establecer estado de fuego a 0 (sin fuego)

        if victim == "v":  # Verificar si el POI es una víctima
            tile.numberOfVictims += 1  # Aumentar el número de víctimas en la casilla
            self.truePOIs -= 1  # Disminuir el conteo de POIs verdaderos
        else:
            self.falsePOIs -= 1  # Disminuir el conteo de POIs falsos

        # Imprimir datos relacionados con POI
        self.appendAffectedTile(tile, "stand", 0, 0)  # Agregar información de casilla afectada
        self.affectedTiles = []  # Reiniciar la lista de casillas afectadas


    def replenishPOIs(self):
        # Mientras haya menos de 3 POIs actuales y más de 0 POIs totales
        while self.currentPOIS < 3 and self.numOfPOIs > 0:
            x = self.random.randint(1, self.grid.width - 2)  # Obtener una coordenada x aleatoria dentro de la cuadrícula
            y = self.random.randint(1, self.grid.height - 2)  # Obtener una coordenada y aleatoria dentro de la cuadrícula
            tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]  # Obtener la casilla en la posición aleatoria

            numF = self.falsePOIs  # Obtener el conteo de POIs falsos
            numV = self.truePOIs if self.truePOIs > 0 else 1  # Obtener el conteo de POIs verdaderos, asegurando que sea al menos 1
            chance = numF / numV  # Calcular la razón de probabilidad de POIs falsos a verdaderos

            # Elegir aleatoriamente un número entre 1 y 100
            random_number = self.random.randint(1, 100)

            # Determinar si generar un POI falso o verdadero basado en la probabilidad
            if (chance > random_number / 100):  # Si la probabilidad es mayor que el número aleatorio
                self.spawnPOI(x, y, tile, "f")  # Generar un POI falso
                numF -= 1  # Disminuir el conteo de POIs falsos
            else:
                self.spawnPOI(x, y, tile, "v")  # Generar un POI verdadero
                numV -= 1  # Disminuir el conteo de POIs verdaderos

        # Imprimir la ubicación de las casillas con .hasPOI
        self.POIsPositions = []  # Inicializar la lista para mantener posiciones de POIs
        for i in range(self.grid.width - 1):  # Iterar sobre el ancho de la cuadrícula
            for j in range(self.grid.height - 1):  # Iterar sobre la altura de la cuadrícula
                for obj in self.grid.get_cell_list_contents([(i, j)]):  # Verificar cada objeto en la celda de la cuadrícula
                    if isinstance(obj, Tile) and obj.hasPOI:  # Si el objeto es una Casilla y tiene un POI
                        self.POIsPositions.append(obj.pos)  # Agregar la posición de la casilla con POI


    def step(self):
        self.affectedTiles = []  # Reiniciar la lista de casillas afectadas para este paso

        self.dictionaryList.append(self.currentAgentsDictionary)  # Agregar el diccionario de agentes actuales a la lista
        self.currentAgentsDictionary = {}  # Reiniciar el diccionario de agentes actuales
        self.datacollector.collect(self)

        if self.damageCounter >= 24 or self.deadVictims >= 4:  # Verificar condiciones de pérdida
            if self.damageCounter >= 24:  # Si el daño excede el límite
                self.demolishedLose += 1  # Aumentar el conteo de pérdidas por demolición
            elif self.deadVictims >= 4:  # Si han muerto demasiadas víctimas
                self.deadVictimLose += 1  # Aumentar el conteo de pérdidas por víctimas muertas
            self.running = False  # Establecer running a False para terminar el juego
            return
        # Verificar si se ganaron suficientes víctimas
        elif self.savedVictims >= 7:  # Verificar si se han salvado suficientes víctimas para ganar
            self.win += 1  # Aumentar el conteo de victorias
            self.running = False  # Establecer running a False para terminar el juego
            return
        else:
            self.schedule.step()  # Proceder al siguiente paso en el programador
            self.steps += 1  # Incrementar el conteo de pasos

    def killFirefighter(self, tile):
        # Verificar si hay algún bombero en la casilla
        if len(tile.hasFireFighter) > 0:
            for firefighter in tile.hasFireFighter:  # Iterar a través de cada bombero en la casilla

                if firefighter.carrying == True:  # Verificar si el bombero está cargando una víctima
                    firefighter.carrying = False  # Establecer estado de carga a False
                    self.deadVictims += 1  # Incrementar el conteo de víctimas muertas
                # Mover el bombero a su posición inicial
                firefighter.move(firefighter.initialPos)


    def throwDice(self):
        # Generar coordenadas x e y aleatorias dentro de los límites de la cuadrícula
        x = self.random.randint(1, self.grid.width - 2)
        y = self.random.randint(1, self.grid.height - 2)

        # Obtener la casilla en las coordenadas generadas
        tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]
        if tile.fireStatus == 0:  # Verificar si la casilla no tiene fuego
            tile.fireStatus = 1  # Establecer el estado de fuego a 1 (indicando que el fuego está comenzando)
            self.appendAffectedTile(tile, "stand", 0, 0)  # Agregar la casilla como afectada

            self.affectedTiles = []  # Reiniciar la lista de casillas afectadas
            # Verificar la casilla de abajo
            if x + 1 <= self.grid.width - 2:
                bottom_tile = [obj for obj in self.grid.get_cell_list_contents([(x + 1, y)]) if isinstance(obj, Tile)][0]
                if bottom_tile.fireStatus == 2 and (tile.wall.bottom == 0 or (tile.wall.isDoor == 3 and tile.wall.isOpen)):
                    tile.fireStatus = 2  # Establecer el estado de fuego a 2 (indicando propagación de fuego)
                    self.spreadFire(x, y)  # Propagar fuego desde la casilla actual

             # Verificar la casilla de arriba
            if x - 1 >= 1:
                top_tile = [obj for obj in self.grid.get_cell_list_contents([(x - 1, y)]) if isinstance(obj, Tile)][0]
                if top_tile.fireStatus == 2 and (tile.wall.top == 0 or (tile.wall.isDoor == 1 and tile.wall.isOpen)):
                    tile.fireStatus = 2  # Establecer el estado de fuego a 2
                    self.spreadFire(x, y)  # Propagar fuego

            # Verificar la casilla de la izquierda
            if y - 1 >= 1:
                left_tile = [obj for obj in self.grid.get_cell_list_contents([(x, y - 1)]) if isinstance(obj, Tile)][0]
                if left_tile.fireStatus == 2 and (tile.wall.left == 0 or (tile.wall.isDoor == 2 and tile.wall.isOpen)):
                    tile.fireStatus = 2  # Establecer el estado de fuego a 2
                    self.spreadFire(x, y)  # Propagar fuego

            # Verificar la casilla de la derecha
            if y + 1 <= self.grid.height - 2:
                right_tile = [obj for obj in self.grid.get_cell_list_contents([(x, y + 1)]) if isinstance(obj, Tile)][0]
                if right_tile.fireStatus == 2 and (tile.wall.right == 0 or (tile.wall.isDoor == 4 and tile.wall.isOpen)):
                    tile.fireStatus = 2  # Establecer el estado de fuego a 2
                    self.spreadFire(x, y)  # Propagar fuego

            # Si la casilla ya tiene fuego y tiene un POI, revelarlo y matar la víctima si está presente
            if tile.fireStatus == 2:
                self.revealPOI(tile)  # Revelar el POI en la casilla
                self.killFirefighter(tile)  # Matar cualquier bombero en la casilla

        elif tile.fireStatus == 1:  # Si la casilla está actualmente comenzando a arder
            tile.fireStatus = 2  # Establecer el estado de fuego a 2 (indicando propagación de fuego)
            self.killFirefighter(tile)  # Matar cualquier bombero en la casilla

            # Si la casilla con fuego tiene un POI, revelarlo y matar la víctima si está presente
            self.revealPOI(tile)  # Revelar el POI
            self.spreadFire(x, y)  # Propagar fuego desde la casilla actual

        elif tile.fireStatus == 2:  # Si la casilla ya está en llamas
            self.makeExplosion(x, y)  # Activar una explosión en las coordenadas
            self.affectedTiles = []  # Reiniciar la lista de casillas afectadas


    def moveDirection(self, x, y, dx, dy):
        # Verificar si la posición actual está dentro de los límites de la cuadrícula
        if x < 1 or y < 1 or x > self.grid.width-2 or y > self.grid.height-2:
            return

        # Obtener la casilla actual en las coordenadas especificadas
        current_tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]

        # Verificar si hay humo en la casilla actual
        if current_tile.fireStatus == 1 or current_tile.fireStatus == 0:
            current_tile.fireStatus = 2

            # Matar el bombero si está presente en la casilla actual
            self.killFirefighter(current_tile)
            # Si la casilla con fuego tiene un POI, revelarlo y matar la víctima si está presente
            self.revealPOI(current_tile)
            self.spreadFire(x, y)
            return

        # Verificar si hay una pared en la dirección que el agente quiere moverse
        if (dx == -1 and (current_tile.wall.top != 0 or (current_tile.wall.isDoor == 1 and current_tile.wall.isOpen is False and current_tile.wall.topHealth > 0))) or \
         (dx == 1 and (current_tile.wall.bottom != 0 or (current_tile.wall.isDoor == 3 and current_tile.wall.isOpen is False and current_tile.wall.bottomHealth > 0))) or \
          (dy == -1 and (current_tile.wall.left != 0 or (current_tile.wall.isDoor == 2 and current_tile.wall.isOpen is False and current_tile.wall.leftHealth > 0))) or \
           (dy == 1 and (current_tile.wall.right != 0 or (current_tile.wall.isDoor == 4 and current_tile.wall.isOpen is False and current_tile.wall.rightHealth > 0))):

            # Si se mueve hacia una pared, incrementar el contador de daño
            if not ((current_tile.wall.top == 2 and dx == -1) or (current_tile.wall.left == 2 and dy == -1) or
              (current_tile.wall.bottom == 2 and dx == 1) or (current_tile.wall.right == 2 and dy == 1)):
                self.damageCounter += 1

            # Moverse hacia arriba
            if dx == -1:
                # Verificar si no está en el límite superior
                if x != 1:
                    # Obtener la casilla arriba de la actual
                    other_tile = [obj for obj in self.grid.get_cell_list_contents([(x+dx, y+dy)]) if isinstance(obj, Tile)][0]
                    other_tile.wall.bottomHealth -= 2
                    # Verificar si la salud de la pared es cero o menor
                    if other_tile.wall.bottomHealth <= 0:
                        other_tile.wall.bottomHealth = 0
                        other_tile.wall.bottom = 0

                        # Actualizar el grafo para búsqueda de rutas
                        if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                            self.graph[(x+dx, y+dy)][(x, y)] = 1
                    else:
                        if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                            self.graph[(x+dx, y+dy)][(x, y)] = 3

                    # Marcar la otra casilla como afectada
                    self.appendAffectedTile(other_tile,"stand", 0, 0)

                # Reducir la salud de la pared superior de la casilla actual
                current_tile.wall.topHealth -= 2

                # Verificar si la salud de la pared es cero o menor
                if current_tile.wall.topHealth <= 0:
                    current_tile.wall.topHealth = 0
                    current_tile.wall.top = 0
                    # Propagar fuego si la pared es destruida
                    self.spreadFire(x, y)

                    # Actualizar el grafo para búsqueda de rutas
                    if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                        self.graph[(x, y)][(x+dx, y+dy)] = 1
                else:
                    if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                        self.graph[(x, y)][(x+dx, y+dy)] = 3

                # Marcar la casilla actual como afectada
                self.appendAffectedTile(current_tile,"stand", 0, 0)

            # Moverse hacia abajo
            elif dx == 1:
                # Verificar si no está en el límite inferior
                if x != self.grid.width - 2:
                    # Obtener la casilla debajo de la actual
                    other_tile = [obj for obj in self.grid.get_cell_list_contents([(x+dx, y+dy)]) if isinstance(obj, Tile)][0]
                    other_tile.wall.topHealth -= 2
                    # Verificar si la salud de la pared es cero o menor
                    if other_tile.wall.topHealth <= 0:
                        other_tile.wall.topHealth = 0
                        other_tile.wall.top = 0
                        # Actualizar el grafo para búsqueda de rutas
                        if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                            self.graph[(x+dx, y+dy)][(x, y)] = 1
                    else:
                        if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                            self.graph[(x+dx, y+dy)][(x, y)] = 3

                    # Marcar la otra casilla como afectada
                    self.appendAffectedTile(other_tile, "stand", 0, 0)

                # Reducir la salud de la pared inferior de la casilla actual
                current_tile.wall.bottomHealth -= 2
                # Verificar si la salud de la pared es cero o menor
                if current_tile.wall.bottomHealth <= 0:
                    current_tile.wall.bottomHealth = 0
                    current_tile.wall.bottom = 0
                    # Propagar fuego si la pared es destruida
                    self.spreadFire(x, y)
                    # Actualizar el grafo para búsqueda de rutas
                    if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                        self.graph[(x, y)][(x+dx, y+dy)] = 1
                else:
                    if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                        self.graph[(x, y)][(x+dx, y+dy)] = 3

                # Marcar la otra casilla como afectada
                self.appendAffectedTile(current_tile,"stand", 0, 0)

            # Moverse hacia la izquierda
            elif dy == -1:
                # Verificar si no está en el límite izquierdo
                if y != 1:
                    # Obtener la casilla a la izquierda de la actual
                    other_tile = [obj for obj in self.grid.get_cell_list_contents([(x+dx, y+dy)]) if isinstance(obj, Tile)][0]
                    other_tile.wall.rightHealth -= 2
                    # Verificar si la salud de la pared es cero o menor
                    if other_tile.wall.rightHealth <= 0:
                        other_tile.wall.rightHealth = 0
                        other_tile.wall.right = 0
                        # Actualizar el grafo para búsqueda de rutas
                        if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                            self.graph[(x+dx, y+dy)][(x, y)] = 1
                    else:
                        if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                            self.graph[(x+dx, y+dy)][(x, y)] = 3

                    # Marcar la otra casilla como afectada
                    self.appendAffectedTile(other_tile,"stand", 0, 0)

                # Reducir la salud de la pared izquierda de la casilla actual
                current_tile.wall.leftHealth -= 2
                # Verificar si la salud de la pared es cero o menor
                if current_tile.wall.leftHealth <= 0:
                    current_tile.wall.leftHealth = 0
                    current_tile.wall.left = 0
                    # Propagar fuego si la pared es destruida
                    self.spreadFire(x, y)
                    # Actualizar el grafo para búsqueda de rutas
                    if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                        self.graph[(x, y)][(x+dx, y+dy)] = 1
                else:
                    if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                        self.graph[(x, y)][(x+dx, y+dy)] = 3

                # Marcar la otra casilla como afectada
                self.appendAffectedTile(current_tile,"stand", 0, 0)

            # Moverse hacia la derecha
            elif dy == 1:
                # Verificar si no está en el límite derecho
                if y != self.grid.height - 2:
                    # Obtener la casilla a la derecha de la actual
                    other_tile = [obj for obj in self.grid.get_cell_list_contents([(x+dx, y+dy)]) if isinstance(obj, Tile)][0]
                    other_tile.wall.leftHealth -= 2
                    # Verificar si la salud de la pared es cero o menor
                    if other_tile.wall.leftHealth <= 0:
                        other_tile.wall.leftHealth = 0
                        other_tile.wall.left = 0
                        # Actualizar el grafo para búsqueda de rutas
                        if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                            self.graph[(x+dx, y+dy)][(x, y)] = 1
                    else:
                        if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                            self.graph[(x+dx, y+dy)][(x, y)] = 3

                    # Marcar la otra casilla como afectada
                    self.appendAffectedTile(other_tile,"stand", 0, 0)

                # Reducir la salud de la pared derecha de la casilla actual
                current_tile.wall.rightHealth -= 2
                # Verificar si la salud de la pared es cero o menor
                if current_tile.wall.rightHealth <= 0:
                    current_tile.wall.rightHealth = 0
                    current_tile.wall.right = 0
                    # Propagar fuego si la pared es destruida
                    self.spreadFire(x, y)
                    # Actualizar el grafo para búsqueda de rutas
                    if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                        self.graph[(x, y)][(x+dx, y+dy)] = 1
                else:
                    if (x+dx < 6 and x+dx > 0) and (y+dy > 0 and y+dy < 8):
                        self.graph[(x, y)][(x+dx, y+dy)] = 3

                # Marcar la otra casilla como afectada
                self.appendAffectedTile(current_tile,"stand", 0, 0)
            return

        # Moverse a la siguiente posición basado en la dirección dada
        new_x = x + dx
        new_y = y + dy

        # Llamada recursiva para continuar moviéndose en la dirección especificada
        self.moveDirection(new_x, new_y, dx, dy)


    def makeExplosion(self, x, y):
        # Recuperar la casilla actual en la posición (x, y)
        current_tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]

        # Moverse hacia abajo desde la posición actual
        self.moveDirection(x, y, 1, 0)

        # Moverse hacia arriba desde la posición actual
        self.moveDirection(x, y, -1, 0)

        # Moverse hacia la izquierda desde la posición actual
        self.moveDirection(x, y, 0, -1)

        # Moverse hacia la derecha desde la posición actual
        self.moveDirection(x, y, 0, 1)

    def spreadFire(self, x, y):
        # Obtener la casilla en la posición (x, y)
        current_tile = [obj for obj in self.grid.get_cell_list_contents([(x, y)]) if isinstance(obj, Tile)][0]

        # Si la casilla en llamas tiene un Punto de Interés (POI), revelarlo y matar la víctima si está presente
        self.revealPOI(current_tile)
        self.appendAffectedTile(current_tile,"stand", 0, 0)

        self.affectedTiles = []  # Inicializar la lista de casillas afectadas
        # Verificar si el fireStatus de la casilla actual no es 0 (no extinguido)
        if current_tile.fireStatus != 0:
            # Verificar y propagar el fuego a casillas adyacentes

            # Moverse hacia abajo a la casilla adyacente inferior
            if x + 1 <= self.grid.width - 2:  # Asegurar que se mantenga dentro de los límites
                bottom_tile = [obj for obj in self.grid.get_cell_list_contents([(x + 1, y)]) if isinstance(obj, Tile)][0]
                # Verificar si la casilla inferior está en llamas y si no hay pared o puerta impidiendo la propagación del fuego
                if bottom_tile.fireStatus == 1 and (current_tile.wall.bottom == 0 or (current_tile.wall.isDoor == 3 and (current_tile.wall.isOpen or current_tile.wall.bottomHealth <= 0))):
                    bottom_tile.fireStatus = 2  # Establecer el estado de fuego de la casilla inferior
                    # Llamar recursivamente para propagar el fuego desde la casilla inferior
                    self.spreadFire(x + 1, y)

            # Moverse hacia arriba a la casilla adyacente superior
            if x - 1 >= 1:  # Asegurar que se mantenga dentro de los límites
                top_tile = [obj for obj in self.grid.get_cell_list_contents([(x - 1, y)]) if isinstance(obj, Tile)][0]
                # Verificar si la casilla superior está en llamas y si no hay pared o puerta impidiendo la propagación del fuego
                if top_tile.fireStatus == 1 and (current_tile.wall.top == 0 or (current_tile.wall.isDoor == 1 and (current_tile.wall.isOpen or current_tile.wall.topHealth <= 0))):
                    top_tile.fireStatus = 2  # Establecer el estado de fuego de la casilla superior
                    # Llamar recursivamente para propagar el fuego desde la casilla superior
                    self.spreadFire(x - 1, y)

            # Moverse hacia la izquierda a la casilla adyacente izquierda
            if y - 1 >= 1:  # Asegurar que se mantenga dentro de los límites
                left_tile = [obj for obj in self.grid.get_cell_list_contents([(x, y - 1)]) if isinstance(obj, Tile)][0]
                # Verificar si la casilla izquierda está en llamas y si no hay pared o puerta impidiendo la propagación del fuego
                if left_tile.fireStatus == 1 and (current_tile.wall.left == 0 or (current_tile.wall.isDoor == 2 and (current_tile.wall.isOpen or current_tile.wall.leftHealth <= 0))):
                    left_tile.fireStatus = 2  # Establecer el estado de fuego de la casilla izquierda
                    # Llamar recursivamente para propagar el fuego desde la casilla izquierda
                    self.spreadFire(x, y - 1)

            # Moverse hacia la derecha a la casilla adyacente derecha
            if y + 1 <= self.grid.height - 2:  # Asegurar que se mantenga dentro de los límites
                right_tile = [obj for obj in self.grid.get_cell_list_contents([(x, y + 1)]) if isinstance(obj, Tile)][0]

                # Verificar si la casilla derecha está en llamas y si no hay pared o puerta impidiendo la propagación del fuego
                if right_tile.fireStatus == 1 and (current_tile.wall.right == 0 or (current_tile.wall.isDoor == 4 and (current_tile.wall.isOpen or current_tile.wall.rightHealth <= 0))):
                    right_tile.fireStatus = 2  # Establecer el estado de fuego de la casilla derecha
                    # Llamar recursivamente para propagar el fuego desde la casilla derecha
                    self.spreadFire(x, y + 1)

    def generateGraph(self, matrix):
        # Obtener el número de filas y columnas en la matriz
        rows = len(matrix)
        cols = len(matrix[0])
        graph = {}  # Inicializar un grafo vacío

        # Iterar a través de cada celda en la matriz usando indexación base-1
        for x in range(1, rows + 1):  # Índice base-1
            for y in range(1, cols + 1):
                node = (x, y)  # Crear un nodo para la posición actual
                graph[node] = {}  # Inicializar la lista de adyacencia para el nodo

                # Asignar variables a cada uno de los 4 números de la matriz
                WXYZ = matrix[x-1][y-1]  # Mantener la cadena original representando las conexiones
                W, X, Y, Z = int(WXYZ[0]), int(WXYZ[1]), int(WXYZ[2]), int(WXYZ[3])  # Analizar los valores de conexión

                # Verificar la dirección ARRIBA (conectar a (x-1, y))
                if W == 0 and x > 1:  # Si no hay pared, conectar con costo 1
                    graph[node][(x-1, y)] = 1
                elif W == 1 and x > 1:  # Si hay pared, conectar con costo 5
                    graph[node][(x-1, y)] = 5

                # Verificar la dirección IZQUIERDA (conectar a (x, y-1))
                if X == 0 and y > 1:  # Si no hay pared, conectar con costo 1
                    graph[node][(x, y-1)] = 1
                elif X == 1 and y > 1:  # Si hay pared, conectar con costo 5
                    graph[node][(x, y-1)] = 5

                # Verificar la dirección ABAJO (conectar a (x+1, y))
                if Y == 0 and x < rows:  # Si no hay pared, conectar con costo 1
                    graph[node][(x+1, y)] = 1
                elif Y == 1 and x < rows:  # Si hay pared, conectar con costo 5
                    graph[node][(x+1, y)] = 5

                # Verificar la dirección DERECHA (conectar a (x, y+1))
                if Z == 0 and y < cols:  # Si no hay pared, conectar con costo 1
                    graph[node][(x, y+1)] = 1
                elif Z == 1 and y < cols:  # Si hay pared, conectar con costo 5
                    graph[node][(x, y+1)] = 5

        return graph  # Devolver el grafo construido

    def addDoorArches(self, graph, door_arches, cost):
        # Iterar a través de cada arco de puerta definido en door_arches
        for arch in door_arches:
            x1, y1, x2, y2 = arch  # Desempaquetar las coordenadas del arco de puerta
            node1 = (x1, y1)  # Crear el primer nodo
            node2 = (x2, y2)  # Crear el segundo nodo

            # Agregar la conexión con el costo especificado si node1 existe en el grafo
            if node1 in graph:
                graph[node1][node2] = cost
            # Agregar la conexión con el costo especificado si node2 existe en el grafo
            if node2 in graph:
                graph[node2][node1] = cost

        return graph  # Devolver el grafo actualizado con arcos de puertas


    def createInitialDictionary(self):
        # Inicializar un diccionario vacío para almacenar datos iniciales de casillas
        self.initialDictionary = {}

        # Iterar a través de las dimensiones de la cuadrícula, excluyendo los bordes externos
        for i in range(1, self.grid.width-1):
            for j in range(1, self.grid.height-1):
                # Recuperar la casilla en la posición actual (i, j)
                tile = [obj for obj in self.grid.get_cell_list_contents([(i, j)]) if isinstance(obj, Tile)][0]
                firefightersIDs = []  # Inicializar una lista para almacenar los IDs únicos de bomberos

                # Iterar a través de los bomberos asignados a la casilla
                for firefighter in tile.hasFireFighter:
                    # Agregar cada ID único de bombero a la lista
                    firefightersIDs.append(firefighter.unique_id)

                # Asignar un diccionario con atributos de casilla al initialDictionary para las coordenadas (i, j)
                self.initialDictionary[(i, j)] = {
                    "top": tile.wall.top,  # Estado de pared superior
                    "left": tile.wall.left,  # Estado de pared izquierda
                    "bottom": tile.wall.bottom,  # Estado de pared inferior
                    "right": tile.wall.right,  # Estado de pared derecha
                    "isOpen": tile.wall.isOpen,  # Estado abierto/cerrado de puerta
                    "topHealth": tile.wall.topHealth,  # Salud de pared superior
                    "leftHealth": tile.wall.leftHealth,  # Salud de pared izquierda
                    "bottomHealth": tile.wall.bottomHealth,  # Salud de pared inferior
                    "rightHealth": tile.wall.rightHealth,  # Salud de pared derecha
                    "fireStatus": tile.fireStatus,  # Estado de fuego en la casilla
                    "hasPoi": tile.hasPOI,  # Booleano indicando si la casilla tiene un Punto de Interés (POI)
                    "numberVictims": tile.numberOfVictims,  # Número de víctimas presentes en la casilla
                    "firefighters": firefightersIDs  # Lista de IDs de bomberos presentes en la casilla
                }
# Definir constantes para las dimensiones de la cuadrícula y número de bomberos
WIDTH = 10
HEIGHT = 8
FIREFIGHTERS = 6
MAX_ITERATIONS = 50
iteration = 0

def process_file(filename):
    # Abrir el archivo especificado en modo lectura
    with open(filename, 'r') as file:
        # Leer todas las líneas del archivo
        lines = file.readlines()

    # Inicializar listas para almacenar diferentes elementos de la simulación
    walls = []
    POIS = []  # Puntos de Interés
    fires = []
    doors = []
    entryPoints = []

    # Leer las primeras 6 líneas para construir la estructura de paredes
    for i in range(6):
        row = []
        binary = lines[i].strip().split()  # Dividir la línea en valores binarios
        for num in binary:
            # Convertir la cadena a una lista de enteros representando propiedades de pared
            wall = [int(num[0]), int(num[1]), int(num[2]), int(num[3])]
            row.append(wall)  # Agregar los datos de pared a la fila
        walls.append(row)  # Agregar la fila a la lista de paredes

    # Leer las líneas restantes para POIs, fuegos, puertas y puntos de entrada
    rest = [line.strip().split() for line in lines[6:]]

    # Analizar Puntos de Interés (POIs)
    for item in rest:
        if len(item) == 3 and item[2] in ['v', 'f']:  # Verificar formato válido de POI
            POIS.append([int(item[0]), int(item[1]), item[2]])  # Agregar datos de POI
        elif len(item) == 2:
            break  # Romper si el formato no coincide

    # Analizar ubicaciones de fuego
    for item in rest:
        if len(item) == 2:
            fires.append([int(item[0]), int(item[1])])  # Agregar coordenadas de fuego
        elif len(item) == 4:
            break  # Romper si el formato no coincide

    # Analizar ubicaciones de puertas
    for item in rest:
        if len(item) == 4:
            doors.append([int(x) for x in item])  # Agregar datos de puerta
        elif len(item) == 2 and [int(item[0]), int(item[1])] not in fires:
            break  # Romper si el formato no coincide

    # Analizar puntos de entrada, invirtiendo el orden para mantener secuencia original
    for item in rest[::-1]:
        if len(item) == 2:
            entryPoints.append((int(item[0]), int(item[1])))  # Agregar coordenadas de punto de entrada
        else:
            break  # Romper si el formato no coincide
    entryPoints.reverse()  # Revertir para restaurar el orden correcto

    return walls, POIS, fires, doors, entryPoints  # Devolver los datos analizados

# Establecer el nombre del archivo para los datos de entrada
filename = "input.txt"
# Procesar el archivo para obtener paredes, POIs, fuegos, puertas y puntos de entrada
walls, POIS, fires, doors, entryPoints = process_file(filename)

# Inicializar el Modelo de Rescate de Incendios con los datos analizados
model = FireRescueModel(FIREFIGHTERS, HEIGHT, WIDTH, entryPoints, walls, doors, fires, POIS)

# Establecer el diccionario inicial
model.createInitialDictionary()

# Ejecutar la simulación mientras el modelo esté activo
while model.running:
    model.step()  # Realizar un paso en la simulación del modelo

# Función para analizar detalles de acción de los datos de entrada
def parse_actions(x):
    return {
        "x": x[0][0],  # coordenada x de la casilla
        "y": x[0][1],  # coordenada y de la casilla
        "top": x[1],  # Estado de pared superior
        "left": x[2],  # Estado de pared izquierda
        "bottom": x[3],  # Estado de pared inferior
        "right": x[4],  # Estado de pared derecha
        "isOpen": x[5],  # Estado abierto/cerrado de puerta
        "topHealth": x[6],  # Salud de pared superior
        "leftHealth": x[7],  # Salud de pared izquierda
        "bottomHealth": x[8],  # Salud de pared inferior
        "rightHealth": x[9],  # Salud de pared derecha
        "fireStatus": x[10],  # Estado de fuego en la casilla
        "hasPOI": x[11],  # Si la casilla tiene un Punto de Interés (POI)
        "numberOfVictims": x[12],  # Número de víctimas en la casilla
        "firefightersIDs": x[13],  # Lista de bomberos presentes en la casilla
        "actions": x[14],  # Acciones realizadas en la casilla
        "dx": x[15],  # Cambio en coordenada x
        "dy": x[16],  # Cambio en coordenada y
        "damageCounter": x[17],  # Contador de daño en la casilla
        "poi": x[18],  # POI en la casilla
        "savedVictims": x[19],  # Número de víctimas salvadas
        "deadVictims": x[20]  # Número de víctimas muertas
    }

# Diccionario para almacenar acciones pendientes
pending_actions = {}

# Bucle a través de cada elemento en la lista de diccionarios del modelo
for (k, v) in enumerate(model.dictionaryList):

    n1_acc = []  # Acumulador para almacenar datos de pasos de agente
    # Bucle a través de cada ID de bot y sus datos asociados
    for xx, xy in v.items():
        n2_acc = []  # Acumulador para datos de casillas afectadas
        # Bucle a través de cada paso del modelo y sus datos
        for yy, y in enumerate(xy):
            n2_acc.append({
                "model_step_id": yy,  # ID del paso del modelo
                "affected_tiles_data": parse_actions(y)  # Analizar los datos de casilla afectada
            })
            n1 = {
                "bot_id": xx,  # ID del bot
                "agent_step_data": n2_acc  # Datos de pasos del agente
            }
            n1_acc.append(n1)  # Agregar los datos de paso del agente a la lista

    # Almacenar los datos del agente acumulados para la ejecución actual
    pending_actions[f"run_{k}"] = n1_acc

# Serializar las acciones pendientes a formato JSON con indentación
parsedJSON = json.dumps(pending_actions, indent=4)

# Definir constantes para las dimensiones de la cuadrícula y número de bomberos
WIDTH = 10
HEIGHT = 8
FIREFIGHTERS = 6
MAX_ITERATIONS = 500
iteration = 0

deadVictimsLoses = 0
wins = 0
demolishedLoses = 0
damageCounter = []
savedVictims = []
deadVictims = []
results = []

# Simulación de 50 ejecuciones
for i in range(50):
    # Procesar el archivo para obtener paredes, POIs, fuegos, puertas y puntos de entrada para cada ejecución
    walls, POIS, fires, doors, entryPoints = process_file(filename)

    model1 = FireRescueModel(FIREFIGHTERS, HEIGHT, WIDTH, entryPoints, walls, doors, fires, POIS)
    while model1.running:
        model1.step()

    # Determinar el resultado
    if model1.win == 1:
        outcome = "Ganaste"
        wins += 1
    elif model1.demolishedLose == 1:
        outcome = "Edificio Destruido"
        demolishedLoses += 1
    elif model1.deadVictimLose == 1:
        outcome = "Victimas Muertas"
        deadVictimsLoses += 1
    else:
        outcome = "Unknown" # Agregar un resultado por defecto en caso de que no se cumplan las condiciones de victoria/derrota

    # Almacenar los resultados de esta ejecución
    damageCounter.append(model1.damageCounter)
    savedVictims.append(model1.savedVictims)
    deadVictims.append(model1.deadVictims)
    results.append({
        "Run": i + 1,
        "Daño": model1.damageCounter,
        "Victimas Salvadas": model1.savedVictims,
        "Victimas Muertas": model1.deadVictims,
        "Estatus": outcome
    })

# Crear un DataFrame de pandas
df = pd.DataFrame(results)

# Mostrar el DataFrame en forma de tabla
print(df)

def parse_actions(x):
    return {
        "x": x[0][0],
        "y": x[0][1],
        "top": x[1],
        "left": x[2],
        "bottom": x[3],
        "right": x[4],
        "isOpen": x[5],
        "topHealth": x[6],
        "leftHealth": x[7],
        "bottomHealth": x[8],
        "rightHealth": x[9],
        "fireStatus": x[10],
        "hasPOI": x[11],
        "numberOfVictims": x[12],
        "firefightersIDs": x[13],
        "actions": x[14],
        "dx": x[15],
        "dy": x[16]
    }

# Asumir que model.dictionaryList[1][0][0] son tus datos
#data = parse_actions(model.dictionaryList[1][0][0])

pending_actions = {}

# Iterar a través de cada elemento en la lista de diccionarios del modelo
for (k, v) in enumerate(model.dictionaryList):

    n1_acc = []  # Acumulador para datos de agentes
    # Iterar a través de cada ID de bot y sus datos asociados
    for xx, xy in v.items():
      n2_acc = []  # Acumulador para datos de pasos del modelo
      # Iterar a través de cada paso y sus datos
      for yy, y in enumerate(xy):
        n2_acc.append({
            "model_step_id": yy,  # ID del paso del modelo
            "affected_tiles_data": parse_actions(y)  # Datos analizados de casillas afectadas
        })

      n1 = {
          "bot_id": xx,  # ID del bot/agente
          "agent_step_data": n2_acc  # Datos de pasos del agente
      }
      n1_acc.append(n1)  # Agregar datos del agente al acumulador
    pending_actions[f"run_{k}"] = n1_acc  # Almacenar datos de la ejecución

# Serializar las acciones pendientes a formato JSON con indentación
parsedJSON = json.dumps(pending_actions, indent=4)

# Escribir los datos JSON a un archivo
with open('bomber_game.json', 'w') as file:
  file.write(parsedJSON)

# TC2008B Modelación de Sistemas Multiagentes con gráficas computacionales
# Python server to interact with Unity via POST
# Sergio Ruiz-Loza, Ph.D. March 2021

from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
import json

class Server(BaseHTTPRequestHandler):
    request_count = 0

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        self._set_response()
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    # Handle POST requests
    def do_POST(self):
        Server.request_count += 1  # Increment request counter
        logging.info(f"POST ACEPTADO #{Server.request_count}")  # Log the request
        tiles = model.initialDictionary  # Retrieve initial dictionary of tiles
        # Serialize the tile data into a dictionary with coordinates as keys
        tiles_serialized = {f"{k[0]},{k[1]}": v for k, v in tiles.items()}

        # If it's the first request, send the tile data
        if Server.request_count == 1:
            self._set_response()  # Set response headers
            self.wfile.write(json.dumps(tiles_serialized).encode('utf-8'))  # Send the serialized tile data
            logging.info("JSON MAPA")  # Log the action
        else:
            self._set_response()  # Set response headers
            self.wfile.write(parsedJSON.encode('utf-8'))  # Send the parsed actions JSON
            logging.info("JSON MOVIMIENTOS")  # Log the action
            Server.request_count = 0  # Reset request counter


def run(server_class=HTTPServer, handler_class=Server, port=8585):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info("HTTP puerto 8585\n") # HTTPD is HTTP Daemon!

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:   # CTRL+C stops the server
        pass
    httpd.server_close()
    logging.info("Stopping httpd...\n")

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()

deadVictimsLoses = 0
wins = 0
demolishedLoses = 0
damageCounter = []
savedVictims = []
deadVictims = []
results = []

# Simulación de 10 ejecuciones
for i in range(50):
    model1 = FireRescueModel(FIREFIGHTERS, HEIGHT, WIDTH, entryPoints, walls, doors, fires, POIS)
    while model1.running:
        model1.step()

    # Determinar el resultado
    if model1.win == 1:
        outcome = "Win"
        wins += 1
    elif model1.demolishedLose == 1:
        outcome = "Lose - Demolished"
        demolishedLoses += 1
    elif model1.deadVictimLose == 1:
        outcome = "Lose - Dead Victims"
        deadVictimsLoses += 1

    # Almacenar los resultados de esta ejecución
    damageCounter.append(model1.damageCounter)
    savedVictims.append(model1.savedVictims)
    deadVictims.append(model1.deadVictims)
    results.append({
        "Run": i + 1,
        "Damage Counter": model1.damageCounter,
        "Saved Victims": model1.savedVictims,
        "Dead Victims": model1.deadVictims,
        "Outcome": outcome
    })
