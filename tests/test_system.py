"""
Suite de Pruebas Automatizadas de Verificación y Validación
Esmeraldas Resiliente | Equipo OpenCode (UTLVTE-9216)
Verifica que todos los componentes y endpoints funcionen al 100%
"""

import sys
import os

# Configuración de ruta base del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_home_page():
    print("[TEST] Probando carga de la pagina principal (index.html)...")
    res = client.get("/")
    assert res.status_code == 200
    assert "Esmeraldas" in res.text
    assert "OpenCode" in res.text
    print("  [OK] Pagina principal responde 200 OK y contiene la identidad de OpenCode.")

def test_system_overview():
    print("[TEST] Probando endpoint /api/overview...")
    res = client.get("/api/overview")
    assert res.status_code == 200
    data = res.json()
    assert "active_incidents_count" in data
    assert "shelter_occupancy_pct" in data
    assert "evacuated_people_count" in data
    print(f"  [OK] Overview validado: {data['active_incidents_count']} incidentes, {data['shelter_occupancy_pct']}% ocupacion.")

def test_gis_endpoints():
    print("[TEST] Probando capas geoespaciales SIG...")
    res_zones = client.get("/api/gis/risk-zones")
    assert res_zones.status_code == 200
    zones = res_zones.json()
    assert len(zones) >= 5
    assert any("50 Casas" in z["name"] for z in zones)
    print(f"  [OK] {len(zones)} zonas de riesgo poligonales cargadas con exito.")

    res_routes = client.get("/api/gis/evacuation-routes")
    assert res_routes.status_code == 200
    routes = res_routes.json()
    assert len(routes) >= 2
    print(f"  [OK] {len(routes)} rutas de evacuacion seguras trazadas.")

def test_ai_prediction_model():
    print("[TEST] Probando Motor de Machine Learning (Random Forest) /api/ai/predict-flood...")
    payload = {
        "sector_name": "50 Casas",
        "precipitation_mm": 110.0,
        "river_level_m": 7.5,
        "soil_saturation_pct": 92.0,
        "elevation_m": 6.0,
        "historical_flood_score": 9.0
    }
    res = client.post("/api/ai/predict-flood", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] in ["Alta", "Crítica"]
    assert data["flood_probability_pct"] > 70.0
    assert len(data["recommended_actions"]) > 0
    print(f"  [OK] Prediccion ML exitosa: Riesgo={data['risk_level']}, Prob={data['flood_probability_pct']}%, Urgencia={data['urgency_score']}.")

def test_ai_nlp_triage():
    print("[TEST] Probando Motor de Triaje NLP /api/ai/triage-report...")
    payload = {
        "text_report": "Urgente mi abuela de 85 anos y dos ninos estan en el techo en 50 Casas el rio Teaone subio muy rapido necesitamos lanchas de rescate",
        "sector": "50 Casas"
    }
    res = client.post("/api/ai/triage-report", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["suggested_severity"] in ["Alta", "Crítica"]
    assert any("lancha" in r.lower() or "bote" in r.lower() for r in data["required_resources"])
    print(f"  [OK] Triaje NLP exitoso: Severidad={data['suggested_severity']}, Urgencia={data['urgency_score']}, Recursos={data['required_resources']}.")

def test_incident_lifecycle():
    print("[TEST] Probando ciclo de vida de un incidente...")
    new_inc = {
        "sector": "San Rafael",
        "category": "Inundación Urbana",
        "description": "El agua de lluvia no drena y se empoza en la calle principal.",
        "latitude": -0.9460,
        "longitude": -79.6605,
        "reported_by": "Test Suite",
        "phone": "0999999999",
        "is_offline_synced": True
    }
    res = client.post("/api/incidents", json=new_inc)
    assert res.status_code == 201
    created = res.json()
    inc_id = created["id"]
    print(f"  [OK] Incidente #{inc_id} registrado con exito con Urgencia={created['urgency_score']} pts.")

    patch_res = client.patch(f"/api/incidents/{inc_id}/status?new_status=En%20Atenci%C3%B3n")
    assert patch_res.status_code == 200
    print(f"  [OK] Incidente #{inc_id} actualizado a 'En Atencion'.")

def test_smart_shelter_relocation():
    print("[TEST] Probando algoritmo de reubicacion optima de albergues...")
    req = {
        "num_people": 10,
        "origin_sector": "50 Casas"
    }
    res = client.post("/api/shelters/relocate", json=req)
    assert res.status_code == 200
    data = res.json()
    assert "recommended_shelter" in data
    assert data["free_capacity"] >= 10
    print(f"  [OK] Albergue recomendado: {data['recommended_shelter']['name']} a {data['distance_km']} km (Capacidad libre: {data['free_capacity']} plazas).")

def test_scenario_load():
    print("[TEST] Probando inyeccion del Escenario Oficial 'Jueves 06:00 AM'...")
    res = client.post("/api/scenario/load-jueves-06am")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    print(f"  [OK] Escenario cargado: {len(data['simulated_events'])} eventos inyectados.")

if __name__ == "__main__":
    print("=" * 60)
    print("EJECUTANDO SUITE DE PRUEBAS DE 'ESMERALDAS RESILIENTE'")
    print("=" * 60)
    test_home_page()
    test_system_overview()
    test_gis_endpoints()
    test_ai_prediction_model()
    test_ai_nlp_triage()
    test_incident_lifecycle()
    test_smart_shelter_relocation()
    test_scenario_load()
    print("=" * 60)
    print("TODAS LAS PRUEBAS PASARON AL 100% EXITOSAMENTE")
    print("=" * 60)
