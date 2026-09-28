"""
Sistema de selección de ruta más rápida - Sistema Integrado de Transporte Masivo
Del Área Metropolitana del valle del Aburra
"""

import heapq
import time
import os

# =================================================================================================================
# 1. BASE DE CONOCIMIENTO (21 Nodos - Línea A)
# =================================================================================================================

LUGARES = {
    'A': 'Niquía', 'B': 'Bello', 'C': 'Madera', 'D': 'Acevedo',
    'E': 'Tricentenario', 'F': 'Caribe', 'G': 'Universidad', 'H': 'Hospital',
    'I': 'Prado', 'J': 'Parque Berrío', 'K': 'San Antonio', 'L': 'Alpujarra',
    'M': 'Exposiciones', 'N': 'Industriales', 'O': 'Poblado', 'P': 'Aguacatala',
    'Q': 'Ayurá', 'R': 'Envigado', 'S': 'Itagüí', 'T': 'Sabaneta', 'U': 'La Estrella'
}

VEHICULOS_DISPONIBLES = ['bus', 'metro', 'carro', 'moto', 'bicicleta']

# Generador Programático del Multígrafo
RED_TRANSPORTE = {k: {} for k in LUGARES.keys()}

def agregar_arista(origen, destino, vehiculos_costos):
    if destino not in RED_TRANSPORTE[origen]:
        RED_TRANSPORTE[origen][destino] = {}
    for vehiculo, costo in vehiculos_costos.items():
        RED_TRANSPORTE[origen][destino][vehiculo] = costo

def hacer_bidireccional(n1, n2, costos):
    agregar_arista(n1, n2, costos)
    agregar_arista(n2, n1, costos)

def construir_grafo():
    """Teje la red interconectada con múltiples capas de complejidad vial."""
    nodos = list(LUGARES.keys())
    
    # 1. Capa Base Secuencial (Metro y calles locales adyacentes)
    for i in range(len(nodos) - 1):
        # Tiempo base en minutos sin alteraciones
        hacer_bidireccional(nodos[i], nodos[i+1], {'metro': 3})
        hacer_bidireccional(nodos[i], nodos[i+1], {'bus': 8, 'carro': 6, 'moto': 4, 'bicicleta': 7})

    # 2. Capa Vías Rápidas (Autopistas y Regional)
    autopista_norte_sur = [('A', 'D'), ('D', 'H'), ('H', 'M'), ('M', 'O'), ('O', 'R'), ('R', 'U')]
    for n1, n2 in autopista_norte_sur:
        hacer_bidireccional(n1, n2, {'carro': 12, 'moto': 8, 'bus': 18})

    av_regional = [('B', 'F'), ('F', 'N'), ('N', 'P'), ('P', 'S')]
    for n1, n2 in av_regional:
        hacer_bidireccional(n1, n2, {'carro': 14, 'moto': 9, 'bus': 20})

    # 3. Capa Centro (Avenida Oriental / Ferrocarril)
    av_oriental = [('H', 'J'), ('J', 'L'), ('L', 'M')]
    for n1, n2 in av_oriental:
        hacer_bidireccional(n1, n2, {'carro': 25, 'moto': 15, 'bus': 35, 'bicicleta': 15})
        
    transversales = [('E', 'I'), ('I', 'K'), ('K', 'O')]
    for n1, n2 in transversales:
        hacer_bidireccional(n1, n2, {'carro': 15, 'moto': 10, 'bicicleta': 15})

construir_grafo()

# =================================================================================================================
# 2. REGLAS LÓGICAS Y SISTEMA EXPERTO
# =================================================================================================================

def regla_ruta_obligatoria(origen: str, destino: str, vehiculo: str) -> list:
    """Regla: Si es 'metro', debe recorrer la línea secuencialmente sin saltos."""
    if vehiculo == 'metro':
        estaciones = list(LUGARES.keys())
        idx_origen = estaciones.index(origen)
        idx_destino = estaciones.index(destino)
        
        if idx_origen <= idx_destino:
            return estaciones[idx_origen:idx_destino+1]
        else:
            return estaciones[idx_destino:idx_origen+1][::-1]
    
    return [origen, destino]

def motor_inferencia_costos(costo_base: int, tipo_transporte: str, hechos: dict) -> float:
    """Calcula los retrasos en minutos basados en las variables de la ciudad."""
    multiplicador = 1.0

    if hechos.get('restriccion_vehicular') and tipo_transporte in ['carro', 'moto']:
        return float('inf')

    if hechos.get('clima') == 'lluvia':
        if tipo_transporte == 'bicicleta': multiplicador *= 3.0
        elif tipo_transporte == 'moto': multiplicador *= 2.0
        elif tipo_transporte in ['bus', 'carro']: multiplicador *= 1.5

    if hechos.get('manifestaciones'):
        if tipo_transporte in ['bus', 'carro']: multiplicador *= 5.0
        elif tipo_transporte == 'moto': multiplicador *= 1.5

    if hechos.get('hora_pico'):
        if tipo_transporte == 'carro': multiplicador *= 2.5
        elif tipo_transporte == 'bus': multiplicador *= 2.0
        elif tipo_transporte == 'metro': multiplicador *= 1.3
        elif tipo_transporte == 'moto': multiplicador *= 1.2

    return costo_base * multiplicador

# =================================================================================================================
# 3. ALGORITMO DE RESOLUCIÓN
# =================================================================================================================

def dijkstra_vehiculo(grafo: dict, inicio: str, fin: str, vehiculo: str, hechos: dict) -> tuple:
    cola = [(0, inicio, [inicio])]
    visitados = {}

    while cola:
        costo_acumulado, nodo_actual, ruta = heapq.heappop(cola)

        if nodo_actual == fin:
            return costo_acumulado, ruta

        for vecino, transportes in grafo.get(nodo_actual, {}).items():
            if vehiculo in transportes:
                costo_real = motor_inferencia_costos(transportes[vehiculo], vehiculo, hechos)
                
                if costo_real == float('inf'):
                    continue
                
                nuevo_costo = costo_acumulado + costo_real
                
                if vecino not in visitados or nuevo_costo < visitados[vecino]:
                    visitados[vecino] = nuevo_costo
                    heapq.heappush(cola, (nuevo_costo, vecino, ruta + [vecino]))
                
    return float('inf'), []

def resolver_ruta(origen: str, destino: str, vehiculo: str, hechos: dict):
    puntos = regla_ruta_obligatoria(origen, destino, vehiculo)
    ruta_total = []
    costo_total = 0.0
    
    for i in range(len(puntos) - 1):
        costo_tramo, ruta_tramo = dijkstra_vehiculo(RED_TRANSPORTE, puntos[i], puntos[i+1], vehiculo, hechos)
        
        if costo_tramo == float('inf'):
            return float('inf'), []
        
        costo_total += costo_tramo
        if not ruta_total:
            ruta_total.extend(ruta_tramo)
        else:
            ruta_total.extend(ruta_tramo[1:])
            
    return costo_total, ruta_total

# =================================================================================================================
# 4. INTERFAZ CLI
# =================================================================================================================

C_VERDE, C_CYAN, C_AMARILLO, C_ROJO, C_RESET = '\033[92m', '\033[96m', '\033[93m', '\033[91m', '\033[0m'

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def imprimir_plan(ruta, vehiculo):
    salida = ""
    for i, nodo in enumerate(ruta):
        nombre = LUGARES.get(nodo, nodo)
        if i == 0:
            salida += f"[{nombre}]"
        else:
            salida += f"\n   |--({C_CYAN}{vehiculo}{C_RESET})--> [{nombre}]"
    print(salida)

def ejecutar_cli():
    while True:
        limpiar_pantalla()
        print(f"{C_VERDE}===================================================================================={C_RESET}")
        print(f"{C_VERDE}            ENRUTAMIENTO AVANZADO: TOPOLOGÍA LÍNEA A (21 NODOS){C_RESET}")
        print(f"{C_VERDE}===================================================================================={C_RESET}")
        
        print(f"\nTerminales principales (de Norte a Sur):")
        nodos = list(LUGARES.items())
        for i in range(0, len(nodos), 2):
            col1 = f"[{C_AMARILLO}{nodos[i][0]}{C_RESET}] {nodos[i][1]:<18}"
            col2 = f"[{C_AMARILLO}{nodos[i+1][0]}{C_RESET}] {nodos[i+1][1]}" if i+1 < len(nodos) else ""
            print(f"  {col1} {col2}")
            
        print("\n(Escriba 'salir' en cualquier momento para terminar)")
        origen = input(f"Origen: ").strip().upper()
        if origen == 'SALIR': break
        
        destino = input(f"Destino: ").strip().upper()
        if destino == 'SALIR': break
        
        if origen not in LUGARES or destino not in LUGARES or origen == destino:
            print(f"{C_ROJO}Ruta inválida.{C_RESET}"); time.sleep(2); continue

        print(f"\n{C_VERDE}Vehículos:{C_RESET} {', '.join(VEHICULOS_DISPONIBLES)}")
        vehiculo = input("Elija su vehículo: ").strip().lower()
        if vehiculo == 'salir': break
        if vehiculo not in VEHICULOS_DISPONIBLES:
            print(f"{C_ROJO}Vehículo no válido.{C_RESET}"); time.sleep(2); continue

        hechos = {'clima': 'despejado', 'manifestaciones': False, 'hora_pico': False, 'restriccion_vehicular': False}
        
        alterar = input(f"\n{C_VERDE}¿Desea ingresar alguna alteración en la ciudad? [y/N]: {C_RESET}").strip().lower()
        if alterar == 'y':
            print(f"\n{C_VERDE}--- Panel de Alteraciones ---{C_RESET}")
            hechos['clima'] = 'lluvia' if input("1. ¿Lluvia fuerte? (s/n): ").strip().lower() == 's' else 'despejado'
            hechos['manifestaciones'] = (input("2. ¿Manifestaciones viales? (s/n): ").strip().lower() == 's')
            hechos['hora_pico'] = (input("3. ¿Es hora pico? (s/n): ").strip().lower() == 's')
            hechos['restriccion_vehicular'] = (input("4. ¿Aplica Pico y Placa? (s/n): ").strip().lower() == 's')

        print(f"{C_AMARILLO}\nCalculando optimización...{C_RESET}")
        time.sleep(1)

        costo, ruta = resolver_ruta(origen, destino, vehiculo, hechos)
        
        limpiar_pantalla()
        print(f"{C_VERDE}===================================================================================={C_RESET}")
        print(f"{C_VERDE}                                 RUTA FINAL{C_RESET}")
        print(f"{C_VERDE}===================================================================================={C_RESET}")
        print(f"Ruta: {LUGARES[origen]} -> {LUGARES[destino]}")
        print(f"Vehículo: {vehiculo.capitalize()} | Estado: {hechos}\n")
        
        if costo == float('inf'):
            print(f"{C_ROJO}[!] Ruta bloqueada con este vehículo por condiciones de la ciudad.{C_RESET}")
        else:
            print(f"{C_VERDE}Plan de Navegación Óptimo:{C_RESET}")
            imprimir_plan(ruta, vehiculo)
            
            saltos_evitados = abs(list(LUGARES.keys()).index(origen) - list(LUGARES.keys()).index(destino)) - (len(ruta) - 1)
            if saltos_evitados > 0:
                print(f"\n    {C_CYAN}* El algoritmo usó vías rápidas evitando {saltos_evitados} paradas intermedias.{C_RESET}")
            

            print(f"\nTiempo estimado de viaje: {costo:.0f} minutos")
            print(f"Puntos en la ruta: {len(ruta)} estaciones/nodos (incluyendo origen y destino)")

        if input(f"\n{C_AMARILLO}¿Calcular nueva ruta? [y/N]: {C_RESET}").strip().lower() != 'y':
            break

if __name__ == "__main__":
    ejecutar_cli()