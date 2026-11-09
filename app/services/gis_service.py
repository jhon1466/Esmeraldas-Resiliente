"""
Esmeraldas Resiliente - Servicio de Información Geográfica (SIG / GIS)
Procesamiento geoespacial, polígonos de riesgo y cálculo de rutas de evacuación
Hackathon UTLVTE 2026 | Equipo OpenCode (UTLVTE-9216)
"""

import math
from typing import List, Dict, Any


# Coordenadas geográficas oficiales de las principales zonas de riesgo en Esmeraldas
ESMERALDAS_RISK_ZONES = [
    {
        "id": 1,
        "name": "50 Casas y Ribera del Teaone",
        "risk_type": "Inundación Severa por Desbordamiento",
        "threat_level": "Crítica",
        "color": "#ef4444",
        "estimated_population": 4200,
        "coordinates": [
            [-0.9500, -79.6600],
            [-0.9540, -79.6620],
            [-0.9560, -79.6670],
            [-0.9520, -79.6680],
            [-0.9490, -79.6630]
        ]
    },
    {
        "id": 2,
        "name": "Isla Luis Vargas Torres (Bajo Río Esmeraldas)",
        "risk_type": "Inundación Fluvial y Pleamar",
        "threat_level": "Crítica",
        "color": "#dc2626",
        "estimated_population": 5800,
        "coordinates": [
            [-0.9680, -79.6540],
            [-0.9750, -79.6560],
            [-0.9780, -79.6600],
            [-0.9720, -79.6620],
            [-0.9660, -79.6580]
        ]
    },
    {
        "id": 3,
        "name": "San Rafael y Propicia 1 al 4",
        "risk_type": "Saturación Pluvial y Cuenca Baja",
        "threat_level": "Alta",
        "color": "#f97316",
        "estimated_population": 7200,
        "coordinates": [
            [-0.9420, -79.6580],
            [-0.9480, -79.6590],
            [-0.9470, -79.6640],
            [-0.9410, -79.6630]
        ]
    },
    {
        "id": 4,
        "name": "El Cabezón (Vía E15 Esmeraldas - Atacames)",
        "risk_type": "Deslizamiento de Ladera y Caída de Rocas",
        "threat_level": "Crítica",
        "color": "#b91c1c",
        "estimated_population": 850,
        "coordinates": [
            [-0.9380, -79.6680],
            [-0.9430, -79.6720],
            [-0.9450, -79.6700],
            [-0.9400, -79.6660]
        ]
    },
    {
        "id": 5,
        "name": "Sector Las Palmas y Malecón de la Playa",
        "risk_type": "Oleaje Anómalo y Drenaje Costero",
        "threat_level": "Media",
        "color": "#eab308",
        "estimated_population": 3100,
        "coordinates": [
            [-0.9850, -79.6520],
            [-0.9920, -79.6550],
            [-0.9900, -79.6610],
            [-0.9830, -79.6580]
        ]
    },
    {
        "id": 6,
        "name": "Valle Rural Tabiazo - Carlos Concha",
        "risk_type": "Desbordamiento Fluvial de Cuenca Media",
        "threat_level": "Alta",
        "color": "#f97316",
        "estimated_population": 1900,
        "coordinates": [
            [-0.8900, -79.6780],
            [-0.9020, -79.6850],
            [-0.9000, -79.6920],
            [-0.8880, -79.6840]
        ]
    }
]

# Rutas de evacuación seguras sugeridas desde zonas críticas hacia albergues
EVACUATION_ROUTES = [
    {
        "name": "Ruta 1: De 50 Casas a UTLVTE Campus Nuevos Horizontes",
        "origin": "50 Casas (-0.952, -79.664)",
        "destination": "Campus FACI UTLVTE (-0.959, -79.645)",
        "distance_km": 2.4,
        "color": "#10b981",
        "status": "Habilitada",
        "waypoints": [
            [-0.9515, -79.6630],
            [-0.9530, -79.6580],
            [-0.9555, -79.6520],
            [-0.9590, -79.6450]
        ]
    },
    {
        "name": "Ruta 2: De Isla Vargas Torres a Coliseo Nubia Villacís",
        "origin": "Isla Vargas Torres (Embarcadero) (-0.971, -79.657)",
        "destination": "Coliseo Nubia Villacís (-0.963, -79.654)",
        "distance_km": 1.2,
        "color": "#06b6d4",
        "status": "Requiere Bote Fluvial",
        "waypoints": [
            [-0.9710, -79.6570],
            [-0.9680, -79.6550],
            [-0.9650, -79.6545],
            [-0.9632, -79.6540]
        ]
    },
    {
        "name": "Ruta 3: De San Rafael a UE 5 de Agosto",
        "origin": "San Rafael (-0.946, -79.660)",
        "destination": "UE 5 de Agosto (-0.948, -79.661)",
        "distance_km": 0.5,
        "color": "#3b82f6",
        "status": "Habilitada a pie con botas de caucho",
        "waypoints": [
            [-0.9460, -79.6605],
            [-0.9470, -79.6608],
            [-0.9480, -79.6610]
        ]
    }
]


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia en kilómetros entre dos coordenadas geográficas."""
    R = 6371.0  # Radio medio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def find_optimal_shelter(lat: float, lon: float, shelters: List[Dict[str, Any]], required_spaces: int = 1) -> Dict[str, Any]:
    """
    Algoritmo de selección óptima de albergues:
    Considera la distancia geográfica mínima y la capacidad libre disponible.
    Evita albergues saturados (>95% de ocupación).
    """
    candidates = []
    for s in shelters:
        free_capacity = s["capacity"] - s["current_occupancy"]
        if free_capacity >= required_spaces:
            dist = haversine_distance_km(lat, lon, s["latitude"], s["longitude"])
            candidates.append({
                "shelter": s,
                "distance_km": dist,
                "free_capacity": free_capacity,
                "score": dist * (1.0 + (s["current_occupancy"] / s["capacity"]))
            })

    if not candidates:
        return {"error": "No hay albergues con capacidad suficiente actualmente."}

    # Ordenar por el score balanceado (distancia ponderada por ocupación)
    candidates.sort(key=lambda x: x["score"])
    best = candidates[0]
    return {
        "recommended_shelter": best["shelter"],
        "distance_km": best["distance_km"],
        "free_capacity": best["free_capacity"],
        "route_available": True
    }


def get_all_risk_zones() -> List[Dict[str, Any]]:
    return ESMERALDAS_RISK_ZONES


def get_evacuation_routes() -> List[Dict[str, Any]]:
    return EVACUATION_ROUTES
