/**
 * Esmeraldas Resiliente - Logica de Control Frontend
 * Hackathon UTLVTE 2026 | Equipo OpenCode (UTLVTE-9216)
 * Modulo de comunicacion asincrona con la API REST y visualizacion cartografica SIG
 */

let map;
let riskZonesLayerGroup;
let incidentsLayerGroup;
let sheltersLayerGroup;
let routesLayerGroup;

// Coordenadas geograficas base de la ciudad de Esmeraldas
const ESMERALDAS_CENTER = [-0.9682, -79.6517];

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initOfflineEngine();
  refreshData();

  // Actualizacion periodica automatica cada 30 segundos
  setInterval(() => {
    refreshData();
  }, 30000);
});

// =========================================================================
// 1. INICIALIZACION DEL MAPA LEAFLET
// =========================================================================
function initMap() {
  map = L.map("map", {
    center: ESMERALDAS_CENTER,
    zoom: 13,
    zoomControl: true
  });

  // Capa base cartografica profesional
  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: "abcd",
    maxZoom: 19
  }).addTo(map);

  riskZonesLayerGroup = L.layerGroup().addTo(map);
  incidentsLayerGroup = L.layerGroup().addTo(map);
  sheltersLayerGroup = L.layerGroup().addTo(map);
  routesLayerGroup = L.layerGroup().addTo(map);

  // Captura de coordenadas mediante clic en el mapa
  map.on("click", (e) => {
    const lat = e.latlng.lat.toFixed(4);
    const lon = e.latlng.lng.toFixed(4);
    const latInput = document.getElementById("repLat");
    const lonInput = document.getElementById("repLon");
    if (latInput && lonInput) {
      latInput.value = lat;
      lonInput.value = lon;
    }
  });
}

function toggleLayer(layerName) {
  if (layerName === "riskZones") {
    const chk = document.getElementById("layerRiskZones").checked;
    chk ? map.addLayer(riskZonesLayerGroup) : map.removeLayer(riskZonesLayerGroup);
  } else if (layerName === "incidents") {
    const chk = document.getElementById("layerIncidents").checked;
    chk ? map.addLayer(incidentsLayerGroup) : map.removeLayer(incidentsLayerGroup);
  } else if (layerName === "shelters") {
    const chk = document.getElementById("layerShelters").checked;
    chk ? map.addLayer(sheltersLayerGroup) : map.removeLayer(sheltersLayerGroup);
  } else if (layerName === "routes") {
    const chk = document.getElementById("layerRoutes").checked;
    chk ? map.addLayer(routesLayerGroup) : map.removeLayer(routesLayerGroup);
  }
}

// =========================================================================
// 2. CARGA Y CONSULTA DE DATOS OPERATIVOS
// =========================================================================
async function refreshData() {
  await loadOverview();
  await loadRiskZones();
  await loadIncidents();
  await loadShelters();
  await loadEvacuationRoutes();
  await loadAlerts();
  await loadFamilies();
}

async function loadOverview() {
  try {
    const res = await fetch("/api/overview");
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("kpiActiveIncidents").innerText = data.active_incidents_count;
    document.getElementById("kpiCriticalCount").innerText = `${data.critical_incidents_count} Criticos`;
    document.getElementById("kpiShelterPct").innerText = `${data.shelter_occupancy_pct}%`;
    document.getElementById("kpiShelterFraction").innerText = `${data.shelter_current_occupancy} / ${data.shelter_total_capacity} plazas`;
    document.getElementById("kpiEvacuated").innerText = data.evacuated_people_count;
    document.getElementById("kpiAlertsCount").innerText = data.active_alerts_count;
  } catch (err) {
    console.error("Error al consultar metricas del sistema:", err);
  }
}

// =========================================================================
// 3. CAPAS GEOESPACIALES: POLIGONOS, MARCADORES Y RUTAS
// =========================================================================
async function loadRiskZones() {
  try {
    const res = await fetch("/api/gis/risk-zones");
    if (!res.ok) return;
    const zones = await res.json();

    riskZonesLayerGroup.clearLayers();
    const listContainer = document.getElementById("riskZonesList");
    if (listContainer) listContainer.innerHTML = "";

    zones.forEach((zone) => {
      const polygon = L.polygon(zone.coordinates, {
        color: zone.color,
        fillColor: zone.color,
        fillOpacity: 0.25,
        weight: 2
      });

      polygon.bindPopup(`
        <div class="text-xs p-1 text-slate-900">
          <div class="font-bold text-sm mb-1">${zone.name}</div>
          <div class="text-slate-700 mb-0.5"><strong>Tipo de Amenaza:</strong> ${zone.risk_type}</div>
          <div class="text-slate-700 mb-0.5"><strong>Nivel:</strong> ${zone.threat_level}</div>
          <div class="text-slate-600"><strong>Poblacion expuesta:</strong> ~${zone.estimated_population.toLocaleString()} habitantes</div>
        </div>
      `);
      riskZonesLayerGroup.addLayer(polygon);

      if (listContainer) {
        const item = document.createElement("div");
        item.className = "p-2 rounded bg-slate-950 hover:bg-slate-900 border border-slate-800 cursor-pointer transition text-xs";
        item.innerHTML = `
          <div class="flex items-center justify-between font-bold text-white mb-0.5">
            <span>${zone.name}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px]" style="background:${zone.color}22; color:${zone.color}; border:1px solid ${zone.color}44">${zone.threat_level}</span>
          </div>
          <div class="text-[11px] text-slate-400">${zone.risk_type}</div>
        `;
        item.onclick = () => {
          map.fitBounds(polygon.getBounds());
          polygon.openPopup();
        };
        listContainer.appendChild(item);
      }
    });
  } catch (err) {
    console.error("Error al cargar zonas de riesgo:", err);
  }
}

async function loadIncidents() {
  try {
    const res = await fetch("/api/incidents");
    if (!res.ok) return;
    const incidents = await res.json();

    incidentsLayerGroup.clearLayers();
    const container = document.getElementById("incidentsList");
    if (container) container.innerHTML = "";

    incidents.forEach((inc) => {
      let markerColor = "#dc2626";
      if (inc.severity === "Alta") markerColor = "#ea580c";
      if (inc.severity === "Media") markerColor = "#ca8a04";
      if (inc.severity === "Baja") markerColor = "#16a34a";

      const circle = L.circleMarker([inc.latitude, inc.longitude], {
        radius: 8,
        fillColor: markerColor,
        color: "#ffffff",
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.9
      });

      circle.bindPopup(`
        <div class="text-xs p-1 text-slate-900" style="min-width: 190px;">
          <div class="font-bold text-sm mb-1">${inc.category}</div>
          <div class="text-slate-700 mb-0.5"><strong>Sector:</strong> ${inc.sector}</div>
          <div class="text-slate-600 mb-1">${inc.description}</div>
          <div class="flex items-center justify-between text-[11px] pt-1 border-t border-slate-200 mt-1">
            <span class="font-bold" style="color:${markerColor}">Severidad: ${inc.severity}</span>
            <span class="text-slate-600">${inc.status}</span>
          </div>
        </div>
      `);
      incidentsLayerGroup.addLayer(circle);

      if (container) {
        const card = document.createElement("div");
        card.className = "p-3 rounded bg-slate-950 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs";
        card.innerHTML = `
          <div class="space-y-1 flex-grow">
            <div class="flex items-center gap-2">
              <span class="font-bold text-white">${inc.sector}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-semibold" style="background:${markerColor}22; color:${markerColor}; border:1px solid ${markerColor}44">
                ${inc.severity} (${inc.urgency_score} pts)
              </span>
              <span class="px-2 py-0.5 rounded text-[10px] bg-slate-900 text-slate-300 border border-slate-800">
                ${inc.category}
              </span>
            </div>
            <p class="text-slate-300 text-[11px]">${inc.description}</p>
            <div class="text-[10px] text-slate-400 flex items-center gap-3">
              <span><i class="fa-regular fa-clock me-1"></i> ${inc.timestamp}</span>
              <span><i class="fa-solid fa-user me-1"></i> ${inc.reported_by}</span>
              ${inc.is_offline_synced ? '<span class="text-cyan-400 font-mono"><i class="fa-solid fa-cloud-arrow-up"></i> Sincronizado Offline</span>' : ''}
            </div>
          </div>
          <div class="flex items-center gap-2 w-full sm:w-auto">
            <select onchange="updateIncidentStatus(${inc.id}, this.value)" class="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1">
              <option value="Pendiente" ${inc.status === 'Pendiente' ? 'selected' : ''}>Pendiente</option>
              <option value="En Atención" ${inc.status === 'En Atención' ? 'selected' : ''}>En Atencion</option>
              <option value="Atendido / Resuelto" ${inc.status === 'Atendido / Resuelto' ? 'selected' : ''}>Atendido / Resuelto</option>
            </select>
          </div>
        `;
        container.appendChild(card);
      }
    });
  } catch (err) {
    console.error("Error al cargar incidentes:", err);
  }
}

async function updateIncidentStatus(id, newStatus) {
  try {
    const res = await fetch(`/api/incidents/${id}/status?new_status=${encodeURIComponent(newStatus)}`, {
      method: "PATCH"
    });
    if (res.ok) {
      refreshData();
    }
  } catch (err) {
    console.error("Error al actualizar estado del incidente:", err);
  }
}

async function loadShelters() {
  try {
    const res = await fetch("/api/shelters");
    if (!res.ok) return;
    const shelters = await res.json();

    sheltersLayerGroup.clearLayers();
    const grid = document.getElementById("sheltersCardsGrid");
    if (grid) grid.innerHTML = "";

    shelters.forEach((s) => {
      let iconColor = s.occupancy_pct >= 95 ? "#dc2626" : (s.occupancy_pct >= 75 ? "#ea580c" : "#0284c7");
      const shelterMarker = L.circleMarker([s.latitude, s.longitude], {
        radius: 10,
        fillColor: iconColor,
        color: "#ffffff",
        weight: 2,
        fillOpacity: 0.95
      });

      shelterMarker.bindPopup(`
        <div class="text-xs p-1 text-slate-900" style="min-width: 200px;">
          <div class="font-bold text-sm text-blue-800 mb-0.5"><i class="fa-solid fa-campground me-1"></i> ${s.name}</div>
          <div class="text-slate-600 mb-1">${s.address} (${s.sector})</div>
          <div class="mb-1 text-slate-700">
            <strong>Ocupacion:</strong> ${s.current_occupancy} / ${s.capacity} (${s.occupancy_pct}%)
          </div>
          <div class="text-[11px] text-slate-600 space-y-0.5 pt-1 border-t border-slate-200">
            <div><i class="fa-solid fa-droplet text-blue-600 me-1"></i> Agua Potable: ${s.water_supply_level}%</div>
            <div><i class="fa-solid fa-box-open text-amber-600 me-1"></i> Raciones Alimentos: ${s.food_supply_level}%</div>
            <div><i class="fa-solid fa-kit-medical text-red-600 me-1"></i> Puesto Medico: ${s.has_medical_post ? 'Disponible' : 'No disponible'}</div>
          </div>
        </div>
      `);
      sheltersLayerGroup.addLayer(shelterMarker);

      if (grid) {
        const card = document.createElement("div");
        card.className = "p-3 rounded bg-slate-950 border border-slate-800 space-y-2 text-xs";
        card.innerHTML = `
          <div class="flex items-center justify-between font-bold text-white">
            <span class="text-blue-300 flex items-center gap-1.5"><i class="fa-solid fa-house-chimney-medical"></i> ${s.name}</span>
            <span class="px-2 py-0.5 rounded text-[10px]" style="background:${iconColor}22; color:${iconColor}; border:1px solid ${iconColor}44">${s.status}</span>
          </div>
          <div class="text-slate-400 text-[11px]">${s.address} &bull; ${s.sector}</div>
          
          <div>
            <div class="flex justify-between text-[11px] mb-1">
              <span class="text-slate-300">Capacidad Utilizada:</span>
              <span class="font-mono font-bold text-white">${s.current_occupancy} / ${s.capacity} (${s.occupancy_pct}%)</span>
            </div>
            <div class="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
              <div class="h-2 rounded-full transition-all" style="width: ${Math.min(100, s.occupancy_pct)}%; background:${iconColor}"></div>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800/80 text-slate-300">
            <div><i class="fa-solid fa-droplet text-blue-400 me-1"></i> Agua: <strong class="${s.water_supply_level < 30 ? 'text-red-400' : 'text-emerald-400'}">${s.water_supply_level}%</strong></div>
            <div><i class="fa-solid fa-box-open text-amber-400 me-1"></i> Viveres: <strong class="${s.food_supply_level < 30 ? 'text-red-400' : 'text-emerald-400'}">${s.food_supply_level}%</strong></div>
          </div>
        `;
        grid.appendChild(card);
      }
    });
  } catch (err) {
    console.error("Error al cargar albergues:", err);
  }
}

async function loadEvacuationRoutes() {
  try {
    const res = await fetch("/api/gis/evacuation-routes");
    if (!res.ok) return;
    const routes = await res.json();

    routesLayerGroup.clearLayers();
    routes.forEach((r) => {
      const polyline = L.polyline(r.waypoints, {
        color: r.color,
        weight: 3.5,
        dashArray: "5, 6",
        opacity: 0.95
      });

      polyline.bindPopup(`
        <div class="text-xs p-1 text-slate-900">
          <div class="font-bold text-sm text-emerald-800 mb-0.5">${r.name}</div>
          <div class="text-slate-600">Distancia aproximada: ${r.distance_km} km</div>
          <div class="text-slate-700">Estado de transitabilidad: <strong>${r.status}</strong></div>
        </div>
      `);
      routesLayerGroup.addLayer(polyline);
    });
  } catch (err) {
    console.error("Error al cargar rutas de evacuacion:", err);
  }
}

async function loadAlerts() {
  try {
    const res = await fetch("/api/alerts");
    if (!res.ok) return;
    const alerts = await res.json();

    const container = document.getElementById("alertsContainer");
    if (!container) return;
    container.innerHTML = "";

    alerts.forEach((a) => {
      let badgeStyle = a.level === "Roja" ? "bg-red-950 text-red-300 border-red-800" : "bg-amber-950 text-amber-300 border-amber-800";
      const div = document.createElement("div");
      div.className = "p-2.5 rounded bg-slate-950 border border-slate-800 space-y-1 text-xs";
      div.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold text-white">${a.title}</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold border ${badgeStyle}">${a.level}</span>
        </div>
        <div class="text-slate-400 text-[10px]">${a.sector} &bull; ${a.timestamp}</div>
        <p class="text-slate-300 text-[11px]">${a.message}</p>
      `;
      container.appendChild(div);
    });
  } catch (err) {
    console.error("Error al cargar alertas:", err);
  }
}

async function loadFamilies() {
  try {
    const res = await fetch("/api/families");
    if (!res.ok) return;
    const families = await res.json();

    const container = document.getElementById("familiesList");
    if (!container) return;
    container.innerHTML = "";

    families.forEach((f) => {
      const div = document.createElement("div");
      div.className = "p-2 bg-slate-950 rounded border border-slate-800 space-y-0.5";
      div.innerHTML = `
        <div class="flex items-center justify-between font-bold text-slate-200">
          <span>${f.head_of_family}</span>
          <span class="text-emerald-400 font-mono text-[11px]">${f.num_members} miembros</span>
        </div>
        <div class="text-slate-400 text-[10px]">${f.sector} &bull; ${f.vulnerable_members}</div>
        <div class="text-slate-300 text-[10px]">Necesidades prioritarias: ${f.urgent_needs}</div>
      `;
      container.appendChild(div);
    });
  } catch (err) {
    console.error("Error al cargar familias:", err);
  }
}

// =========================================================================
// 4. CONTROL DE PESTANAS
// =========================================================================
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach((p) => p.classList.add("hidden"));
  document.querySelectorAll(".nav-tab").forEach((b) => {
    b.classList.remove("active", "bg-slate-800", "text-white", "border-slate-700");
    b.classList.add("bg-slate-950", "text-slate-400");
  });

  const selected = document.getElementById(tabId);
  if (selected) selected.classList.remove("hidden");

  const activeBtn = Array.from(document.querySelectorAll(".nav-tab")).find((b) =>
    b.getAttribute("onclick")?.includes(tabId)
  );
  if (activeBtn) {
    activeBtn.classList.remove("bg-slate-950", "text-slate-400");
    activeBtn.classList.add("active", "bg-slate-800", "text-white", "border-slate-700");
  }

  if (tabId === "tab-gis") {
    setTimeout(() => {
      map.invalidateSize();
    }, 150);
  }
}

// =========================================================================
// 5. MOTOR DE INTELIGENCIA ARTIFICIAL: MACHINE LEARNING
// =========================================================================
async function handleAIPredict(e) {
  e.preventDefault();
  const sector = document.getElementById("aiSector").value;
  const precip = parseFloat(document.getElementById("inputPrecip").value);
  const river = parseFloat(document.getElementById("inputRiver").value);
  const soil = parseFloat(document.getElementById("inputSoil").value);
  const elev = parseFloat(document.getElementById("inputElev").value);

  const container = document.getElementById("aiPredictionResult");
  container.innerHTML = '<div class="text-xs text-cyan-400 flex items-center gap-2"><i class="fa-solid fa-spinner fa-spin"></i> Ejecutando inferencia Random Forest...</div>';

  try {
    const res = await fetch("/api/ai/predict-flood", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sector_name: sector,
        precipitation_mm: precip,
        river_level_m: river,
        soil_saturation_pct: soil,
        elevation_m: elev,
        historical_flood_score: 8.5
      })
    });

    if (!res.ok) throw new Error("Error en la inferencia");
    const data = await res.json();

    let borderClass = data.risk_level === "Crítica" ? "border-red-600 bg-red-950/20" : (data.risk_level === "Alta" ? "border-amber-600 bg-amber-950/20" : "border-emerald-600 bg-emerald-950/20");
    let actionsHtml = data.recommended_actions.map((a) => `<li class="flex items-start gap-1.5"><i class="fa-solid fa-angle-right text-cyan-400 mt-0.5"></i> <span>${a}</span></li>`).join("");

    container.innerHTML = `
      <div class="p-2.5 rounded border ${borderClass} space-y-1.5">
        <div class="flex items-center justify-between">
          <span class="font-bold text-white text-xs">${data.sector_name}</span>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-900 border border-slate-700">${data.risk_level}</span>
        </div>
        <div class="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800">
          <div>Probabilidad de Inundacion: <strong class="font-mono text-cyan-300">${data.flood_probability_pct}%</strong></div>
          <div>Indice de Urgencia: <strong class="font-mono text-amber-300">${data.urgency_score}/100</strong></div>
          <div class="col-span-2">Poblacion estimada en riesgo: <strong class="text-white">${data.estimated_affected_people.toLocaleString()} personas</strong></div>
        </div>
      </div>

      <div class="space-y-1 pt-1 text-[11px]">
        <div class="font-bold text-slate-200">Disposiciones Prescriptivas del Modelo:</div>
        <ul class="space-y-0.5 text-slate-300">${actionsHtml}</ul>
      </div>
      <div class="text-[10px] text-slate-500 font-mono text-right pt-1 border-t border-slate-800">Modelo Calibrado: ${data.model_version}</div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-red-400">Fallo en la inferencia: ${err.message}</div>`;
  }
}

// =========================================================================
// 6. MOTOR DE INTELIGENCIA ARTIFICIAL: TRIAJE NLP
// =========================================================================
function loadNLPCase(num) {
  const input = document.getElementById("nlpInputText");
  if (num === 1) {
    input.value = "Urgente, se desbordo el rio Teaone en 50 Casas, el agua entra con fuerza a las viviendas y hay una abuela de 84 anos y dos bebes atrapados en el techo, requerimos lanchas y rescate inmediato.";
  } else if (num === 2) {
    input.value = "Deslizamiento de piedras y lodo en el sector El Cabezon via Esmeraldas a Atacames, la carretera esta bloqueada en ambos carriles, dos vehiculos quedaron atrapados.";
  } else if (num === 3) {
    input.value = "En el Coliseo Nubia Villacis se agotaron los botellones de agua potable y los sueros orales, ninos presentan deshidratacion y se solicitan medicamentos basicos.";
  }
}

async function handleAITriage(e) {
  e.preventDefault();
  const text = document.getElementById("nlpInputText").value;
  const container = document.getElementById("aiTriageResult");
  container.innerHTML = '<div class="text-xs text-purple-400 flex items-center gap-2"><i class="fa-solid fa-spinner fa-spin"></i> Procesando semantica y entidades de emergencia...</div>';

  try {
    const res = await fetch("/api/ai/triage-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text_report: text, sector: "" })
    });

    if (!res.ok) throw new Error("Error en triaje semantico");
    const data = await res.json();

    let entitiesBadge = data.key_entities.map((ent) => `<span class="px-2 py-0.5 rounded bg-purple-950 text-purple-200 border border-purple-800 text-[10px]">${ent}</span>`).join(" ");
    let resourcesBadge = data.required_resources.map((rec) => `<li class="flex items-center gap-1.5"><i class="fa-solid fa-truck-medical text-amber-400"></i> ${rec}</li>`).join("");

    container.innerHTML = `
      <div class="p-2.5 rounded bg-slate-950 border border-slate-800 space-y-1.5 text-xs">
        <div class="flex items-center justify-between">
          <span class="font-bold text-white text-xs">${data.detected_category}</span>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 text-red-400 border border-red-900">${data.suggested_severity} (Prioridad: ${data.urgency_score} pts)</span>
        </div>
        
        <div class="space-y-0.5">
          <div class="text-slate-400 font-semibold text-[11px]">Entidades identificadas:</div>
          <div class="flex flex-wrap gap-1">${entitiesBadge || '<span class="text-slate-500">Sin entidades especificas</span>'}</div>
        </div>

        <div class="space-y-0.5 pt-1 border-t border-slate-800">
          <div class="text-slate-400 font-semibold text-[11px]">Recursos recomendados:</div>
          <ul class="space-y-0.5 text-slate-300 text-[11px]">${resourcesBadge}</ul>
        </div>

        <div class="text-[10px] text-slate-400 italic pt-1 border-t border-slate-800/80">
          ${data.triage_notes}
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="text-xs text-red-400">Fallo en triaje: ${err.message}</div>`;
  }
}

// =========================================================================
// 7. MOTOR OFFLINE Y REPORTE CIUDADANO
// =========================================================================
function initOfflineEngine() {
  const badge = document.getElementById("networkStatusBadge");
  const badgeText = document.getElementById("networkStatusText");

  function updateStatus() {
    if (navigator.onLine) {
      if (badge) {
        badge.className = "flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold bg-slate-800 text-emerald-400 border border-slate-700";
        badgeText.innerText = "Conectado (En linea)";
      }
      syncOfflineReports();
    } else {
      if (badge) {
        badge.className = "flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800";
        badgeText.innerText = "Modo Offline (Sin conexion)";
      }
    }
    updateOfflineQueueUI();
  }

  window.addEventListener("online", updateStatus);
  window.addEventListener("offline", updateStatus);
  updateStatus();
}

function getBrowserGPS() {
  if ("geolocation" in navigator) {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        document.getElementById("repLat").value = pos.coords.latitude.toFixed(4);
        document.getElementById("repLon").value = pos.coords.longitude.toFixed(4);
      },
      () => {
        alert("No fue posible obtener coordenadas GPS automaticamente. Puedes ingresarlas manualmente o seleccionar un punto en el mapa.");
      }
    );
  }
}

async function handleCitizenReport(e) {
  e.preventDefault();
  const report = {
    sector: document.getElementById("repSector").value,
    category: document.getElementById("repCategory").value,
    description: document.getElementById("repDescription").value,
    latitude: parseFloat(document.getElementById("repLat").value),
    longitude: parseFloat(document.getElementById("repLon").value),
    reported_by: document.getElementById("repName").value || "Ciudadano anonimo",
    phone: document.getElementById("repPhone").value || "",
    is_offline_synced: false
  };

  if (!navigator.onLine) {
    saveOfflineReport(report);
    alert("Sin conexion a internet detectada. El reporte ha sido guardado de forma segura en el almacenamiento local (Modo Offline) y se transmitira automaticamente al restablecer la red.");
    document.getElementById("formCitizenReport").reset();
    return;
  }

  try {
    const res = await fetch("/api/incidents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report)
    });

    if (res.ok) {
      alert("Reporte de emergencia registrado exitosamente en el Centro de Operaciones.");
      document.getElementById("formCitizenReport").reset();
      refreshData();
      switchTab("tab-gis");
    } else {
      throw new Error("Fallo en la peticion de envio");
    }
  } catch {
    saveOfflineReport(report);
    alert("Aviso de red: El reporte fue respaldado en almacenamiento local y se sincronizara tan pronto se reanude la comunicacion.");
  }
}

function saveOfflineReport(report) {
  let queue = JSON.parse(localStorage.getItem("opencode_offline_reports") || "[]");
  report.is_offline_synced = true;
  queue.push(report);
  localStorage.setItem("opencode_offline_reports", JSON.stringify(queue));
  updateOfflineQueueUI();
}

async function syncOfflineReports() {
  let queue = JSON.parse(localStorage.getItem("opencode_offline_reports") || "[]");
  if (queue.length === 0) return;

  const remaining = [];
  for (const item of queue) {
    try {
      const res = await fetch("/api/incidents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item)
      });
      if (!res.ok) remaining.push(item);
    } catch {
      remaining.push(item);
    }
  }

  localStorage.setItem("opencode_offline_reports", JSON.stringify(remaining));
  updateOfflineQueueUI();
  if (remaining.length === 0) {
    refreshData();
  }
}

function updateOfflineQueueUI() {
  let queue = JSON.parse(localStorage.getItem("opencode_offline_reports") || "[]");
  const countBadge = document.getElementById("kpiOfflineQueue");
  if (countBadge) countBadge.innerText = queue.length;

  const container = document.getElementById("offlineQueueContainer");
  const itemsDiv = document.getElementById("offlineQueueItems");
  if (container && itemsDiv) {
    if (queue.length > 0) {
      container.classList.remove("hidden");
      itemsDiv.innerHTML = queue
        .map((q) => `<div class="p-1 rounded bg-slate-900 border border-slate-800 flex justify-between"><span>${q.sector}: ${q.category}</span><span class="text-amber-400">En cola local</span></div>`)
        .join("");
    } else {
      container.classList.add("hidden");
    }
  }
}

// =========================================================================
// 8. REUBICACION OPTIMA DE ALBERGUES
// =========================================================================
async function handleRelocate(e) {
  e.preventDefault();
  const origin = document.getElementById("relocOrigin").value;
  const num = parseInt(document.getElementById("relocPeople").value);
  const container = document.getElementById("relocateResult");

  try {
    const res = await fetch("/api/shelters/relocate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ origin_sector: origin, num_people: num })
    });
    const data = await res.json();

    if (data.error) {
      container.innerHTML = `<span class="text-red-400 font-bold">${data.error}</span>`;
      return;
    }

    const s = data.recommended_shelter;
    container.innerHTML = `
      <div class="space-y-1">
        <div class="font-bold text-emerald-400 text-xs flex items-center gap-1"><i class="fa-solid fa-circle-check"></i> Albergue Optimo Recomendado:</div>
        <div class="text-white font-bold">${s.name}</div>
        <div class="text-slate-300 text-[10px]">${s.address} (${s.sector})</div>
        <div class="grid grid-cols-2 gap-1 text-[10px] pt-1 border-t border-slate-800">
          <div>Distancia: <strong class="text-white">${data.distance_km} km</strong></div>
          <div>Capacidad disponible: <strong class="text-emerald-400">${data.free_capacity} plazas</strong></div>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<span class="text-red-400">Error al calcular albergue: ${err.message}</span>`;
  }
}

// =========================================================================
// 9. EMISION DE ALERTAS
// =========================================================================
async function handleCreateAlert(e) {
  e.preventDefault();
  const alertData = {
    title: document.getElementById("alertTitle").value,
    sector: document.getElementById("alertSector").value,
    level: document.getElementById("alertLevel").value,
    message: document.getElementById("alertMessage").value
  };

  try {
    const res = await fetch("/api/alerts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(alertData)
    });
    if (res.ok) {
      alert("Alerta oficial publicada y difundida con exito.");
      document.getElementById("formCreateAlert").reset();
      refreshData();
    }
  } catch (err) {
    console.error("Error al emitir alerta:", err);
  }
}

// =========================================================================
// 10. CARGA DEL ESCENARIO OFICIAL DE PRUEBA: "JUEVES 06:00 AM"
// =========================================================================
async function loadSimulationScenario() {
  if (!confirm("Confirmacion: Se inyectara el Escenario Oficial 'Jueves 06:00 AM' del reto 'Esmeraldas Resiliente'. Se restableceran los albergues e incidentes de prueba de la FACI.")) {
    return;
  }

  try {
    const res = await fetch("/api/scenario/load-jueves-06am", { method: "POST" });
    const data = await res.json();
    alert("Escenario Oficial Jueves 06:00 AM cargado correctamente.");
    await refreshData();
    switchTab("tab-gis");
  } catch (err) {
    alert("Fallo al cargar escenario: " + err.message);
  }
}
