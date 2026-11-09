"""
Esmeraldas Resiliente - Aplicación Principal y API REST (FastAPI)
Proyecto Hackathon UTLVTE 2026 | Facultad de Ingenierías (FACI)
Equipo: OpenCode (Código: UTLVTE-9216) - 9no Ciclo "A" - Carrera de TI
Lema: «Programar hoy para proteger vidas mañana»
"""

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from datetime import datetime
import os
from typing import List, Optional

from app.database import get_db_connection, init_database, reset_to_scenario_data
from app.models.schemas import (
    Incident, IncidentCreate, IncidentStatus, SeverityLevel,
    Shelter, ShelterRelocateRequest,
    Alert, AlertCreate,
    AffectedFamily,
    AIPredictionRequest, AIPredictionResponse,
    AITriageRequest, AITriageResponse,
    SystemOverview
)
from app.services.gis_service import (
    get_all_risk_zones, get_evacuation_routes, find_optimal_shelter
)
from app.services.ai_service import ai_risk_model, ai_nlp_triage

# Inicializar Base de Datos SQLite
init_database()

app = FastAPI(
    title="Esmeraldas Resiliente API",
    description="""
    **Plataforma Integral de Prevención, Monitoreo y Gestión de Emergencias ante el Fenómeno El Niño en Esmeraldas.**
    Desarrollado para el **Hackathon UTLVTE 2026 (INNOVA-TI)** por el equipo **OpenCode**.
    
    * Integra los 6 módulos: SIG interactivo, Reporte Ciudadano Offline, Panel COE, Albergues/Evacuación, Familias y Motor de Inteligencia Artificial Predictiva.
    * Evaluado bajo el escenario de simulación oficial: *Jueves, 06:00 AM*.
    """,
    version="2.0.0",
    contact={
        "name": "Equipo OpenCode (UTLVTE-9216)",
        "email": "leandro.moreira.granda@utelvt.edu.ec",
        "url": "https://github.com/jhon1466/Esmeraldas-Resiliente"
    }
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# =========================================================================
# 1. OVERVIEW & ESTADÍSTICAS DEL SISTEMA
# =========================================================================

@app.get("/api/overview", response_model=SystemOverview, tags=["1. Mando & Control COE"])
def get_system_overview():
    """Retorna las métricas clave en tiempo real para el Centro de Operaciones de Emergencia (COE)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM incidents WHERE status != 'Atendido / Resuelto'")
    active_incidents = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count FROM incidents WHERE severity = 'Crítica' AND status != 'Atendido / Resuelto'")
    critical_incidents = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) as count, SUM(capacity) as cap, SUM(current_occupancy) as occ FROM shelters")
    shelter_row = cursor.fetchone()
    total_shelters = shelter_row["count"] or 0
    total_cap = shelter_row["cap"] or 1
    total_occ = shelter_row["occ"] or 0
    occ_pct = round((total_occ / total_cap) * 100.0, 1) if total_cap > 0 else 0.0

    cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE active = 1")
    active_alerts = cursor.fetchone()["count"]

    cursor.execute("SELECT SUM(num_members) as sum_evac FROM affected_families")
    evac_sum = cursor.fetchone()["sum_evac"] or total_occ

    conn.close()

    return SystemOverview(
        active_incidents_count=active_incidents,
        critical_incidents_count=critical_incidents,
        total_shelters_count=total_shelters,
        shelter_total_capacity=total_cap,
        shelter_current_occupancy=total_occ,
        shelter_occupancy_pct=occ_pct,
        active_alerts_count=active_alerts,
        evacuated_people_count=evac_sum,
        simulation_mode=True
    )


# =========================================================================
# 2. MÓDULO 2 & 3: INCIDENTES Y REPORTES CIUDADANOS
# =========================================================================

@app.get("/api/incidents", response_model=List[Incident], tags=["2. Incidentes & Reportes"])
def list_incidents(
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    severity: Optional[str] = Query(None, description="Filtrar por severidad"),
    status: Optional[str] = Query(None, description="Filtrar por estado")
):
    """Consulta todos los incidentes georreferenciados con soporte de filtros."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM incidents WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY urgency_score DESC, id DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.post("/api/incidents", response_model=Incident, status_code=status.HTTP_201_CREATED, tags=["2. Incidentes & Reportes"])
def create_incident(incident: IncidentCreate):
    """
    Registra un nuevo incidente ciudadano (vía web o sincronización offline).
    Aplica automáticamente el motor de NLP para triaje y cálculo de urgencia.
    """
    # Triaje NLP automático
    triage_res = ai_nlp_triage.analyze(AITriageRequest(
        text_report=incident.description,
        sector=incident.sector
    ))

    severity = triage_res.suggested_severity.value
    urgency_score = triage_res.urgency_score
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO incidents (sector, description, latitude, longitude, category, severity, status, reported_by, phone, urgency_score, is_offline_synced, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, 'Pendiente', ?, ?, ?, ?, ?)
    """, (
        incident.sector,
        incident.description,
        incident.latitude,
        incident.longitude,
        incident.category.value,
        severity,
        incident.reported_by,
        incident.phone or "",
        urgency_score,
        1 if incident.is_offline_synced else 0,
        timestamp
    ))
    new_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM incidents WHERE id = ?", (new_id,))
    created_row = dict(cursor.fetchone())
    conn.close()

    return created_row


@app.patch("/api/incidents/{incident_id}/status", tags=["2. Incidentes & Reportes"])
def update_incident_status(incident_id: int, new_status: IncidentStatus):
    """Permite al COE actualizar el estado de atención de un incidente."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE incidents SET status = ? WHERE id = ?", (new_status.value, incident_id))
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    conn.commit()
    conn.close()
    return {"message": "Estado de incidente actualizado exitosamente", "incident_id": incident_id, "new_status": new_status.value}


# =========================================================================
# 3. MÓDULO 4: ALBERGUES Y REUBICACIÓN INTELIGENTE
# =========================================================================

@app.get("/api/shelters", response_model=List[Shelter], tags=["3. Albergues & Evacuación"])
def list_shelters():
    """Retorna la lista de albergues con su estado de capacidad y suministros."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shelters ORDER BY current_occupancy DESC")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d["occupancy_pct"] = round((d["current_occupancy"] / d["capacity"]) * 100.0, 1)
        # Actualizar estatus dinámicamente
        if d["occupancy_pct"] >= 95.0:
            d["status"] = "Lleno / Crítico"
        elif d["occupancy_pct"] >= 75.0:
            d["status"] = "Casi Lleno"
        else:
            d["status"] = "Disponible"
        result.append(d)
    return result


@app.post("/api/shelters/relocate", tags=["3. Albergues & Evacuación"])
def smart_relocate(req: ShelterRelocateRequest):
    """
    Algoritmo de balanceo inteligente de albergues:
    Encuentra el albergue disponible más cercano evitando saturar los que están al límite.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shelters")
    shelters = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Coordenadas aproximadas según sector de origen
    sector_coords = {
        "50 Casas": (-0.9515, -79.6630),
        "San Rafael": (-0.9460, -79.6605),
        "Isla Vargas Torres": (-0.9710, -79.6570),
        "Tabiazo": (-0.8950, -79.6820),
        "Tachina": (-0.9780, -79.6250)
    }
    coords = sector_coords.get(req.origin_sector, (-0.9632, -79.6540))

    relocation_result = find_optimal_shelter(coords[0], coords[1], shelters, req.num_people)
    return relocation_result


# =========================================================================
# 4. MÓDULO 3: ALERTAS TEMPRANAS DEL COE
# =========================================================================

@app.get("/api/alerts", response_model=List[Alert], tags=["4. Alertas & COE"])
def list_alerts():
    """Retorna las alertas emitidas por el COE Cantonal/Provincial."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts WHERE active = 1 ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/alerts", response_model=Alert, status_code=status.HTTP_201_CREATED, tags=["4. Alertas & COE"])
def create_alert(alert: AlertCreate):
    """Emite una nueva alerta oficial para sectores vulnerables."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO alerts (title, sector, level, message, timestamp, active)
    VALUES (?, ?, ?, ?, ?, 1)
    """, (alert.title, alert.sector, alert.level.value, alert.message, timestamp))
    new_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM alerts WHERE id = ?", (new_id,))
    created = dict(cursor.fetchone())
    conn.close()
    return created


# =========================================================================
# 5. MÓDULO 5: FAMILIAS AFECTADAS Y ASISTENCIA
# =========================================================================

@app.get("/api/families", response_model=List[AffectedFamily], tags=["5. Asistencia Humanitaria"])
def list_families():
    """Consulta el censo de familias evacuadas y asistencia humanitaria."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM affected_families ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =========================================================================
# 6. MÓDULO 1: SISTEMA DE INFORMACIÓN GEOGRÁFICA (SIG)
# =========================================================================

@app.get("/api/gis/risk-zones", tags=["6. SIG & Cartografía"])
def get_risk_zones():
    """Retorna los polígonos de zonas de alto riesgo georreferenciadas en Esmeraldas."""
    return get_all_risk_zones()


@app.get("/api/gis/evacuation-routes", tags=["6. SIG & Cartografía"])
def get_routes():
    """Retorna las rutas seguras de evacuación hacia albergues."""
    return get_evacuation_routes()


# =========================================================================
# 7. MÓDULO 6: INTELIGENCIA ARTIFICIAL & MACHINE LEARNING
# =========================================================================

@app.post("/api/ai/predict-flood", response_model=AIPredictionResponse, tags=["7. Inteligencia Artificial (Eje OpenCode)"])
def predict_flood_risk(req: AIPredictionRequest):
    """
    Predice la probabilidad de inundación y nivel de severidad mediante el modelo
    de Machine Learning (Random Forest) calibrado con datos hidrológicos de Esmeraldas.
    """
    return ai_risk_model.predict(req)


@app.post("/api/ai/triage-report", response_model=AITriageResponse, tags=["7. Inteligencia Artificial (Eje OpenCode)"])
def triage_emergency_report(req: AITriageRequest):
    """
    Triaje automatizado por Procesamiento de Lenguaje Natural (NLP).
    Extrae categoría, entidades vulnerables y recursos de emergencia a partir del texto ciudadano.
    """
    return ai_nlp_triage.analyze(req)


# =========================================================================
# 8. SIMULADOR DEL ESCENARIO OFICIAL: "JUEVES, 06:00 AM"
# =========================================================================

@app.post("/api/scenario/load-jueves-06am", tags=["8. Simulación Demo Day"])
def load_scenario_jueves_06am():
    """
    Carga de forma instantánea el Escenario Oficial 'Jueves 06:00 AM'
    para la demostración en vivo ante el jurado calificador.
    """
    reset_to_scenario_data()
    return {
        "status": "success",
        "message": "Escenario Oficial 'Jueves 06:00 AM' cargado con éxito.",
        "simulated_events": [
            "Inundaciones urbanas en 50 Casas y San Rafael",
            "Desbordamiento de Río Esmeraldas en zona rural Tabiazo",
            "Deslizamiento e interrupción en vía E15 El Cabezón",
            "Familias y niños aislados en Isla Vargas Torres requiriendo lanchas",
            "Albergue Coliseo Nubia Villacís al 95% requiriendo reubicación inteligente y suministros"
        ]
    }


# =========================================================================
# SERVIDORES DE ARCHIVOS ESTÁTICOS / APLICACIÓN WEB
# =========================================================================

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_home():
    """Sirve la página web principal e interactiva."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Esmeraldas Resiliente API funcionando. Visita /docs para la documentación interactiva."}
