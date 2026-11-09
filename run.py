"""
Esmeraldas Resiliente - Script de Ejecución Local
Hackathon UTLVTE 2026 | Equipo OpenCode (UTLVTE-9216)
Carrera de Tecnologías de la Información - 9no Ciclo "A"

Ejecución del servidor web y API REST:
    python run.py
"""

import uvicorn
import os
import sys

# Agregar la ruta raiz del proyecto al path de Python
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    print("=" * 70)
    print("INICIANDO SISTEMA: ESMERALDAS RESILIENTE - HACKATHON UTLVTE 2026")
    print("Equipo: OpenCode (Codigo UTLVTE-9216) - 9no Ciclo Paralelo 'A'")
    print("Carrera: Ingenieria en Tecnologias de la Informacion - FACI")
    print("Servidor HTTP: http://localhost:8000")
    print("Documentacion Swagger API: http://localhost:8000/docs")
    print("Consola Operativa SIG y COE: http://localhost:8000/")
    print("=" * 70)

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
