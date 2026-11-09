-- =============================================================================
-- ESMERALDAS RESILIENTE - ESQUEMA DE BASE DE DATOS GEOGRÁFICA (PostgreSQL / PostGIS)
-- Proyecto Oficial Hackathon UTLVTE 2026 | Equipo OpenCode (UTLVTE-9216)
-- Entregable Oficial N.º 4: Base de Datos y Modelo Geográfico
-- =============================================================================

-- 1. Habilitar extensiones geoespaciales y de UUID
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. ENUMS para tipado estricto
DO $$ BEGIN
    CREATE TYPE severidad_riesgo AS ENUM ('Baja', 'Media', 'Alta', 'Crítica');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE estado_incidente AS ENUM ('Pendiente', 'En Atención', 'Atendido / Resuelto');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE nivel_alerta AS ENUM ('Informativa', 'Amarilla', 'Naranja', 'Roja');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- =============================================================================
-- 3. TABLA: ZONAS DE RIESGO GEORREFERENCIADAS (Polígonos PostGIS)
-- =============================================================================
CREATE TABLE IF NOT EXISTS zonas_riesgo (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    tipo_riesgo VARCHAR(100) NOT NULL,
    amenaza_nivel severidad_riesgo DEFAULT 'Alta',
    poblacion_estimada INTEGER DEFAULT 0,
    geometria GEOMETRY(Polygon, 4326) NOT NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_zonas_riesgo_geom ON zonas_riesgo USING GIST(geometria);

-- =============================================================================
-- 4. TABLA: ALBERGUES TEMPORALES Y CENTROS DE EVACUACIÓN
-- =============================================================================
CREATE TABLE IF NOT EXISTS albergues (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    direccion TEXT NOT NULL,
    capacidad_total INTEGER NOT NULL CHECK (capacidad_total > 0),
    ocupacion_actual INTEGER NOT NULL DEFAULT 0 CHECK (ocupacion_actual >= 0),
    estado VARCHAR(30) DEFAULT 'Disponible',
    tiene_puesto_medico BOOLEAN DEFAULT TRUE,
    nivel_agua_potable INTEGER DEFAULT 100 CHECK (nivel_agua_potable BETWEEN 0 AND 100),
    nivel_alimentos INTEGER DEFAULT 100 CHECK (nivel_alimentos BETWEEN 0 AND 100),
    ubicacion GEOMETRY(Point, 4326) NOT NULL,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_albergues_geom ON albergues USING GIST(ubicacion);

-- =============================================================================
-- 5. TABLA: INCIDENTES Y REPORTES CIUDADANOS (Con puntos PostGIS)
-- =============================================================================
CREATE TABLE IF NOT EXISTS incidentes (
    id SERIAL PRIMARY KEY,
    sector VARCHAR(100) NOT NULL,
    categoria VARCHAR(80) NOT NULL,
    descripcion TEXT NOT NULL,
    severidad severidad_riesgo DEFAULT 'Media',
    estado estado_incidente DEFAULT 'Pendiente',
    reportado_por VARCHAR(120) DEFAULT 'Ciudadano anónimo',
    telefono_contacto VARCHAR(20),
    puntaje_urgencia NUMERIC(5,2) DEFAULT 50.00,
    sincronizado_offline BOOLEAN DEFAULT FALSE,
    ubicacion GEOMETRY(Point, 4326) NOT NULL,
    registrado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_incidentes_geom ON incidentes USING GIST(ubicacion);
CREATE INDEX IF NOT EXISTS idx_incidentes_urgencia ON incidentes(puntaje_urgencia DESC);

-- =============================================================================
-- 6. TABLA: ALERTAS DEL CENTRO DE OPERACIONES DE EMERGENCIA (COE)
-- =============================================================================
CREATE TABLE IF NOT EXISTS alertas_coe (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    sector_afectado TEXT NOT NULL,
    nivel nivel_alerta DEFAULT 'Amarilla',
    mensaje TEXT NOT NULL,
    activa BOOLEAN DEFAULT TRUE,
    emitida_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 7. TABLA: FAMILIAS DAMNIFICADAS Y ASISTENCIA HUMANITARIA
-- =============================================================================
CREATE TABLE IF NOT EXISTS familias_afectadas (
    id SERIAL PRIMARY KEY,
    jefe_familia VARCHAR(150) NOT NULL,
    numero_miembros INTEGER NOT NULL CHECK (numero_miembros > 0),
    sector_origen VARCHAR(100) NOT NULL,
    miembros_vulnerables TEXT,
    albergue_asignado_id INTEGER REFERENCES albergues(id) ON DELETE SET NULL,
    necesidades_urgentes TEXT,
    estado VARCHAR(50) DEFAULT 'Evacuada',
    registrada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- 8. VISTAS OPERATIVAS ESPACIALES
-- =============================================================================

-- Vista que cruza incidentes activos que caen dentro de zonas de alto riesgo
CREATE OR REPLACE VIEW vista_incidentes_en_zonas_criticas AS
SELECT 
    i.id AS incidente_id,
    i.sector,
    i.categoria,
    i.severidad,
    i.puntaje_urgencia,
    z.nombre AS zona_nombre,
    z.amenaza_nivel,
    ST_AsGeoJSON(i.ubicacion) AS geojson_punto
FROM incidentes i
JOIN zonas_riesgo z ON ST_Contains(z.geometria, i.ubicacion)
WHERE i.estado != 'Atendido / Resuelto';

-- Vista de albergues ordenados por capacidad libre
CREATE OR REPLACE VIEW vista_capacidad_albergues AS
SELECT 
    id,
    nombre,
    sector,
    capacidad_total,
    ocupacion_actual,
    (capacidad_total - ocupacion_actual) AS cupos_disponibles,
    ROUND(((ocupacion_actual::decimal / capacidad_total) * 100), 1) AS porcentaje_ocupacion,
    nivel_agua_potable,
    nivel_alimentos
FROM albergues
ORDER BY porcentaje_ocupacion DESC;
