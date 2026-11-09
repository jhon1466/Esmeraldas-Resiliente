"""
Esmeraldas Resiliente - Capa de Datos y Persistencia
Gestión de SQLite local con compatibilidad para esquemas PostgreSQL/PostGIS
Hackathon UTLVTE 2026 | Equipo OpenCode (UTLVTE-9216)
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "resiliente.db")


def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Inicializa las tablas y pobla los datos del escenario si la base de datos es nueva."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabla de Incidentes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sector TEXT NOT NULL,
        description TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'Media',
        status TEXT NOT NULL DEFAULT 'Pendiente',
        reported_by TEXT DEFAULT 'Ciudadano anónimo',
        phone TEXT DEFAULT '',
        urgency_score REAL DEFAULT 50.0,
        is_offline_synced INTEGER DEFAULT 0,
        timestamp TEXT NOT NULL
    );
    """)

    # Tabla de Albergues
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shelters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sector TEXT NOT NULL,
        address TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        capacity INTEGER NOT NULL,
        current_occupancy INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'Disponible',
        has_medical_post INTEGER DEFAULT 1,
        water_supply_level INTEGER DEFAULT 100,
        food_supply_level INTEGER DEFAULT 100
    );
    """)

    # Tabla de Alertas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        sector TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        active INTEGER DEFAULT 1
    );
    """)

    # Tabla de Familias Afectadas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS affected_families (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        head_of_family TEXT NOT NULL,
        num_members INTEGER NOT NULL,
        sector TEXT NOT NULL,
        vulnerable_members TEXT NOT NULL,
        assigned_shelter_id INTEGER,
        urgent_needs TEXT NOT NULL,
        status TEXT DEFAULT 'Evacuada',
        FOREIGN KEY(assigned_shelter_id) REFERENCES shelters(id)
    );
    """)

    # Tabla de Zonas de Riesgo Georreferenciadas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS risk_zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        risk_type TEXT NOT NULL,
        threat_level TEXT NOT NULL,
        geojson_polygon TEXT NOT NULL,
        estimated_population INTEGER DEFAULT 0
    );
    """)

    conn.commit()

    # Si no hay albergues, inicializar con los de Esmeraldas
    cursor.execute("SELECT COUNT(*) as count FROM shelters")
    if cursor.fetchone()["count"] == 0:
        seed_initial_data(conn)

    conn.close()


def seed_initial_data(conn):
    """Pobla los albergues oficiales y datos iniciales de la ciudad de Esmeraldas."""
    cursor = conn.cursor()

    shelters = [
        ("Coliseo Nubia Villacís", "Centro / Las Palmas", "Av. Olmedo y Rocafuerte", -0.9632, -79.6540, 250, 230, "Casi Lleno", 1, 35, 40),
        ("Unidad Educativa Luis Vargas Torres", "Centro", "Calle 10 de Agosto", -0.9675, -79.6512, 180, 85, "Disponible", 1, 80, 85),
        ("Campus Nuevos Horizontes UTLVTE", "Nuevos Horizontes", "Ciudadela Universitaria", -0.9590, -79.6450, 300, 45, "Disponible", 1, 95, 90),
        ("Unidad Educativa 5 de Agosto", "Sur / La Propicia", "Av. Universitaria", -0.9480, -79.6610, 150, 142, "Casi Lleno", 0, 20, 25),
        ("Centro Parroquial Tachina", "Tachina Rural", "Frente al Aeropuerto Carlos Concha", -0.9780, -79.6250, 120, 30, "Disponible", 1, 90, 75)
    ]

    cursor.executemany("""
    INSERT INTO shelters (name, sector, address, latitude, longitude, capacity, current_occupancy, status, has_medical_post, water_supply_level, food_supply_level)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, shelters)

    # Alerta Inicial
    cursor.execute("""
    INSERT INTO alerts (title, sector, level, message, timestamp, active)
    VALUES (?, ?, ?, ?, ?, 1)
    """, (
        "Alerta Amarilla Preventiva Provincial",
        "Toda la provincia de Esmeraldas",
        "Amarilla",
        "Monitoreo continuo de cuencas hídricas del Río Esmeraldas y Río Teaone ante precipitaciones atípicas.",
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()


def reset_to_scenario_data():
    """
    Reinicia el sistema e inyecta exactamente los datos del Escenario de Simulación Oficial:
    'Jueves, 06:00 AM' del reto 'Esmeraldas Resiliente 2026'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Limpiar tablas
    cursor.execute("DELETE FROM incidents")
    cursor.execute("DELETE FROM shelters")
    cursor.execute("DELETE FROM alerts")
    cursor.execute("DELETE FROM affected_families")

    # 1. Albergues del Escenario
    # "Un albergue temporal que está próximo a alcanzar su capacidad máxima (Coliseo Nubia Villacís)"
    shelters = [
        ("Coliseo Nubia Villacís", "Centro / Las Palmas", "Av. Olmedo y Rocafuerte", -0.9632, -79.6540, 250, 238, "Casi Lleno", 1, 15, 20),
        ("Campus Nuevos Horizontes UTLVTE", "Nuevos Horizontes", "Ciudadela Universitaria FACI", -0.9590, -79.6450, 350, 60, "Disponible", 1, 95, 90),
        ("Unidad Educativa Luis Vargas Torres", "Centro", "Calle 10 de Agosto", -0.9675, -79.6512, 200, 110, "Disponible", 1, 75, 80),
        ("Unidad Educativa 5 de Agosto", "Sur / La Propicia", "Av. Universitaria", -0.9480, -79.6610, 160, 152, "Casi Lleno", 0, 18, 25),
        ("Casa Comunal Tachina", "Tachina Rural", "Sector Aeropuerto", -0.9780, -79.6250, 120, 25, "Disponible", 1, 85, 75)
    ]
    cursor.executemany("""
    INSERT INTO shelters (name, sector, address, latitude, longitude, capacity, current_occupancy, status, has_medical_post, water_supply_level, food_supply_level)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, shelters)

    # 2. Incidentes del Escenario Oficial 'Jueves 06:00 AM'
    # - Inundaciones en sectores urbanos de la ciudad de Esmeraldas.
    # - Desbordamiento de un río que afecta a comunidades rurales.
    # - Deslizamiento de tierra que interrumpe una carretera.
    # - Familias que requieren asistencia y evacuación.
    # - Solicitudes urgentes de agua potable, alimentos y medicamentos.
    incidents = [
        ("50 Casas - Ribera del Teaone", "Desbordamiento repentino del río Teaone. Nivel de agua supera 1.2m dentro de las viviendas. Familias en los techos.", -0.9515, -79.6630, "Desbordamiento de Río", "Crítica", "En Atención", "COE Cantonal / 911", "0982979921", 96.5, 0, "2026-11-09 06:05"),
        ("San Rafael y Propicia 1", "Inundación urbana generalizada por colapso del sistema de drenaje pluvial. Tránsito vehicular completamente suspendido.", -0.9460, -79.6605, "Inundación Urbana", "Alta", "Pendiente", "Ciudadanía WhatsApp", "0997692084", 84.0, 0, "2026-11-09 06:12"),
        ("Vía E15 Esmeraldas - Atacames (Sector El Cabezón)", "Deslizamiento de ladera con caída de rocas y lodo. Vía principal interrumpida en ambos sentidos. Dos vehículos varados.", -0.9410, -79.6700, "Vía Interrumpida", "Crítica", "En Atención", "Policía Nacional / Tránsito", "0967071133", 92.0, 0, "2026-11-09 06:18"),
        ("Comunidad Rural Tabiazo / Carlos Concha", "Creciente violenta del Río Esmeraldas anega cultivos y amenaza puente colgante peatonal. 30 familias aisladas.", -0.8950, -79.6820, "Desbordamiento de Río", "Alta", "Pendiente", "Tenencia Política Tabiazo", "0979421542", 88.5, 0, "2026-11-09 06:22"),
        ("Coliseo Nubia Villacís", "Urgente: Albergue al 95% de su capacidad. Se agotaron las reservas de agua embotellada y sueros orales infantiles.", -0.9632, -79.6540, "Falta de Suministros", "Crítica", "Pendiente", "Dra. Ramos (Cruz Roja)", "0984123456", 95.0, 0, "2026-11-09 06:30"),
        ("Isla Luis Vargas Torres", "12 personas (incluyendo 4 niños y 2 adultos mayores) atrapadas por subida de marea y río crecido. Requieren rescate en bote con motor fuera de borda.", -0.9710, -79.6570, "Personas Atrapadas / Evacuación", "Crítica", "Pendiente", "Líder Comunitario Isla", "0987654321", 98.0, 0, "2026-11-09 06:35")
    ]
    cursor.executemany("""
    INSERT INTO incidents (sector, description, latitude, longitude, category, severity, status, reported_by, phone, urgency_score, is_offline_synced, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, incidents)

    # 3. Alertas Oficiales
    alerts = [
        ("Alerta Roja: Desbordamiento Ríos Esmeraldas y Teaone", "Sectores Ribereños, 50 Casas, La Propicia e Isla Vargas Torres", "Roja", "Evacuación inmediata obligatoria. Activar protocolos de rescate acuático y movilización de lanchas.", "2026-11-09 06:00", 1),
        ("Alerta Naranja: Cierre Vial E15 Esmeraldas - Atacames", "Tramo El Cabezón - Tonsupa", "Naranja", "Maquinaria pesada del MTOP en camino para despeje. Tomar vías alternas únicamente por la vía Carlos Concha si está habilitada.", "2026-11-09 06:15", 1)
    ]
    cursor.executemany("""
    INSERT INTO alerts (title, sector, level, message, timestamp, active)
    VALUES (?, ?, ?, ?, ?, ?)
    """, alerts)

    # 4. Familias Afectadas
    families = [
        ("Familia Preciado Estupiñán", 6, "50 Casas", "2 niños, 1 adulto mayor con hipertensión", 1, "Agua, frazadas, medicamentos antihipertensivos"),
        ("Familia Quiñónez Batioja", 4, "Isla Luis Vargas Torres", "1 lactante (6 meses), madre gestante", None, "Rescate urgente, fórmula láctea, pañales"),
        ("Familia Montaño Caicedo", 5, "San Rafael", "3 niños escolares", 2, "Kits de alimentos no perecibles, ropa seca"),
        ("Familia Valencia Mina", 7, "Tabiazo Rural", "3 adultos mayores, 2 niños", None, "Evacuación médica por vía fluvial, agua potable")
    ]
    cursor.executemany("""
    INSERT INTO affected_families (head_of_family, num_members, sector, vulnerable_members, assigned_shelter_id, urgent_needs)
    VALUES (?, ?, ?, ?, ?, ?)
    """, families)

    conn.commit()
    conn.close()
    return True
