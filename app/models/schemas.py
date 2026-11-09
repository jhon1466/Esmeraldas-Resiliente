"""
Esmeraldas Resiliente - Modelos y Esquemas de Datos Pydantic
Proyecto Hackathon UTLVTE 2026 | Equipo OpenCode (UTLVTE-9216)
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class SeverityLevel(str, Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"
    CRITICA = "Crítica"


class IncidentCategory(str, Enum):
    INUNDACION = "Inundación Urbana"
    DESBORDAMIENTO = "Desbordamiento de Río"
    DESLIZAMIENTO = "Deslizamiento de Tierra"
    PERSONAS_ATRAPADAS = "Personas Atrapadas / Evacuación"
    VIA_BLOQUEADA = "Vía Interrumpida"
    SUMINISTROS = "Falta de Suministros"
    OTRO = "Otro Incidente"


class IncidentStatus(str, Enum):
    PENDIENTE = "Pendiente"
    EN_ATENCION = "En Atención"
    ATENDIDO = "Atendido / Resuelto"


class IncidentCreate(BaseModel):
    sector: str = Field(..., example="50 Casas")
    description: str = Field(..., example="Desbordamiento de estero, agua alcanzando 1 metro de altura.")
    latitude: float = Field(..., example=-0.9521)
    longitude: float = Field(..., example=-79.6645)
    category: IncidentCategory = IncidentCategory.INUNDACION
    reported_by: Optional[str] = "Ciudadano anónimo"
    phone: Optional[str] = ""
    is_offline_synced: Optional[bool] = False


class Incident(IncidentCreate):
    id: int
    severity: SeverityLevel = SeverityLevel.MEDIA
    status: IncidentStatus = IncidentStatus.PENDIENTE
    timestamp: str
    urgency_score: float = 50.0  # Calculado por motor de IA (0 a 100)


class Shelter(BaseModel):
    id: int
    name: str
    sector: str
    address: str
    latitude: float
    longitude: float
    capacity: int
    current_occupancy: int
    status: str  # "Disponible", "Casi Lleno", "Lleno"
    has_medical_post: bool
    water_supply_level: int  # 0 a 100%
    food_supply_level: int   # 0 a 100%
    occupancy_pct: Optional[float] = None


class ShelterRelocateRequest(BaseModel):
    num_people: int = Field(..., ge=1, example=6)
    origin_sector: str = Field(..., example="50 Casas")


class AlertLevel(str, Enum):
    INFORMATIVA = "Informativa"
    AMARILLA = "Amarilla"
    NARANJA = "Naranja"
    ROJA = "Roja"


class AlertCreate(BaseModel):
    title: str = Field(..., example="Alerta Roja por Crecida del Río Teaone")
    sector: str = Field(..., example="Sectores 50 Casas, San Rafael y Propicia 1")
    level: AlertLevel = AlertLevel.ROJA
    message: str = Field(..., example="Se solicita evacuación preventiva hacia albergues autorizados.")


class Alert(AlertCreate):
    id: int
    timestamp: str
    active: bool = True


class AffectedFamily(BaseModel):
    id: int
    head_of_family: str
    num_members: int
    sector: str
    vulnerable_members: str  # Ej: "2 niños, 1 adulto mayor"
    assigned_shelter_id: Optional[int] = None
    urgent_needs: str  # Ej: "Agua potable, leche, abrigo"
    status: str = "Evacuada"


# Modelos para Inteligencia Artificial
class AIPredictionRequest(BaseModel):
    sector_name: str = Field(..., example="50 Casas")
    precipitation_mm: float = Field(..., ge=0, le=250, example=92.5)
    river_level_m: float = Field(..., ge=0, le=12, example=6.8)
    soil_saturation_pct: float = Field(..., ge=0, le=100, example=88.0)
    elevation_m: float = Field(..., ge=0, le=300, example=8.5)
    historical_flood_score: float = Field(..., ge=0, le=10, example=8.5)


class AIPredictionResponse(BaseModel):
    sector_name: str
    flood_probability_pct: float
    risk_level: SeverityLevel
    urgency_score: float
    estimated_affected_people: int
    recommended_actions: List[str]
    model_version: str = "OpenCode-ML-RiskNet-v2.1"


class AITriageRequest(BaseModel):
    text_report: str = Field(..., example="Urgente el río Teaone se desbordó en San Rafael el agua entra a las casas y hay una abuela atrapada")
    sector: Optional[str] = "San Rafael"


class AITriageResponse(BaseModel):
    detected_category: IncidentCategory
    suggested_severity: SeverityLevel
    urgency_score: float
    key_entities: List[str]
    required_resources: List[str]
    triage_notes: str


class SystemOverview(BaseModel):
    active_incidents_count: int
    critical_incidents_count: int
    total_shelters_count: int
    shelter_total_capacity: int
    shelter_current_occupancy: int
    shelter_occupancy_pct: float
    active_alerts_count: int
    evacuated_people_count: int
    simulation_mode: bool
