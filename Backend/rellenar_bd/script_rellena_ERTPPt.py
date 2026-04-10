#!/usr/bin/env python3
"""
Script para rellenar la base de datos GoVet con datos de:
- Especies
- Razas
- Tutores
- Pacientes
- Tutor_Paciente (relación)
- Consultas (fichas médicas)

Este script NO vacía la base de datos, solo agrega datos.
Usa ON CONFLICT DO NOTHING para evitar duplicados.
"""

import pandas as pd
import psycopg2
import os
import sys
from datetime import datetime, timedelta
import random

print("="*60)
print("SCRIPT DE RELLENO DE BASE DE DATOS GOVET")
print("Especies → Razas → Tutores → Pacientes → Tutor_Paciente → Consultas")
print("="*60)

# Conectar PostgreSQL
try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),         
        dbname=os.getenv("DB_NAME", "govet"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "")
    )
    cur = conn.cursor()
    print("✅ Conexión a la base de datos exitosa\n")
except Exception as e:
    print(f"❌ Error conectando a la base de datos: {e}")
    sys.exit(1)

# =============================================================================
# 1. INSERTAR ESPECIES
# =============================================================================
print("📊 1/6 - Insertando ESPECIES...")
try:
    df_especies = pd.read_csv('/app/rellenar_bd/especies.csv', sep=';')
    especies_insertadas = 0
    
    for _, row in df_especies.iterrows():
        nombre = row['nombre_especie']
        nombre_comun = row['nombre_comun']
        id_especie = row['id_especie'] if 'id_especie' in row and pd.notna(row['id_especie']) else None
        
        if pd.notna(nombre):
            if id_especie:
                cur.execute("""
                    INSERT INTO govet.especie (id_especie, nombre_cientifico, nombre_comun)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id_especie) DO NOTHING;
                """, (id_especie, nombre, nombre_comun))
            else:
                cur.execute("""
                    INSERT INTO govet.especie (id_especie, nombre_cientifico, nombre_comun)
                    VALUES (DEFAULT, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (nombre, nombre_comun))
            especies_insertadas += 1
    
    conn.commit()
    print(f"   ✅ {especies_insertadas} especies procesadas")
except Exception as e:
    print(f"   ❌ Error insertando especies: {e}")
    conn.rollback()

# =============================================================================
# 2. INSERTAR RAZAS
# =============================================================================
print("\n📊 2/6 - Insertando RAZAS...")
try:
    df_razas = pd.read_csv('/app/rellenar_bd/razas.csv', sep=';')
    razas_insertadas = 0
    
    for _, row in df_razas.iterrows():
        nombre = row['nombre']
        id_especie = row['id_especie']
        id_raza = row['id_raza'] if 'id_raza' in row and pd.notna(row['id_raza']) else None
        
        if pd.notna(nombre):
            if id_raza:
                cur.execute("""
                    INSERT INTO govet.raza (id_raza, nombre, id_especie)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id_raza) DO NOTHING;
                """, (id_raza, nombre, id_especie))
            else:
                cur.execute("""
                    INSERT INTO govet.raza (id_raza, nombre, id_especie)
                    VALUES (DEFAULT, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (nombre, id_especie))
            razas_insertadas += 1
    
    conn.commit()
    print(f"   ✅ {razas_insertadas} razas procesadas")
except Exception as e:
    print(f"   ❌ Error insertando razas: {e}")
    conn.rollback()

# =============================================================================
# 3. INSERTAR TUTORES
# =============================================================================
print("\n📊 3/6 - Insertando TUTORES...")
try:
    df_tutores = pd.read_csv('/app/rellenar_bd/tutores.csv', sep=';')
    tutores_insertados = 0
    
    for _, row in df_tutores.iterrows():
        rut = row['Rut']
        nombres = row['Nombres']
        apellidoPaterno = row['ApPaterno']
        apellidoMaterno = row['ApMaterno']
        direccion = row['Direccion']
        region = row['Region']
        comuna = row['Comuna']
        telefono1 = row['Telefono']
        telefono2 = row['Telefono2']
        celular1 = row['Celular']
        celular2 = row['Celular2']
        email = row['Email']
        observacion = row['Observaciones']

        # Convertir teléfonos a int o None
        if pd.notna(telefono1):
            telefono1 = int(telefono1)
        else:
            telefono1 = None

        if pd.notna(telefono2):
            telefono2 = int(telefono2)
        else:
            telefono2 = None

        if pd.notna(celular1):
            celular1 = int(celular1)
        else:
            celular1 = None

        if pd.notna(celular2):
            celular2 = int(celular2)
        else:
            celular2 = None

        # RUT en minúsculas
        rut = rut.lower()

        cur.execute("""
            INSERT INTO govet.tutor (rut, nombre, apellido_paterno, apellido_materno, 
                                     telefono, telefono2, celular, celular2, 
                                     region, comuna, direccion, email, observacion, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING;
        """, (rut, nombres, apellidoPaterno, apellidoMaterno, telefono1, telefono2, 
              celular1, celular2, region, comuna, direccion, email, observacion, True))
        tutores_insertados += 1

    conn.commit()
    print(f"   ✅ {tutores_insertados} tutores procesados")
except Exception as e:
    print(f"   ❌ Error insertando tutores: {e}")
    conn.rollback()

# =============================================================================
# 4. INSERTAR PACIENTES
# =============================================================================
print("\n📊 4/6 - Insertando PACIENTES...")
try:
    df_pacientes = pd.read_csv('/app/rellenar_bd/pacientes.csv', sep=';')
    pacientes_insertados = 0
    
    for _, row in df_pacientes.iterrows():
        nombre = row['NOMBRE']
        color = row['COLOR']
        sexo = row['SEXO_SIGLA']
        esterilizado = row['ESTERILIZADO']
        id_paciente = row['CÓDIGO MASCOTA'] if 'CÓDIGO MASCOTA' in row and pd.notna(row['CÓDIGO MASCOTA']) else None
        
        if pd.notna(esterilizado):
            esterilizado = bool(int(esterilizado))
        else:
            esterilizado = None
            
        fecha_nacimiento = row['FECHA NACIMIENTO']
        id_raza = row['ID_RAZA']
        codigo_chip = row['CHIP']

        if pd.notna(nombre):
            if id_paciente:
                cur.execute("""
                    INSERT INTO govet.paciente (id_paciente, nombre, color, sexo, 
                                               esterilizado, fecha_nacimiento, id_raza, codigo_chip, activo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id_paciente) DO NOTHING;
                """, (id_paciente, nombre, color, sexo, esterilizado, fecha_nacimiento, id_raza, codigo_chip, True))
            else:
                cur.execute("""
                    INSERT INTO govet.paciente (id_paciente, nombre, color, sexo, 
                                               esterilizado, fecha_nacimiento, id_raza, codigo_chip, activo)
                    VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (nombre, color, sexo, esterilizado, fecha_nacimiento, id_raza, codigo_chip, True))
            pacientes_insertados += 1

    conn.commit()
    print(f"   ✅ {pacientes_insertados} pacientes procesados")
except Exception as e:
    print(f"   ❌ Error insertando pacientes: {e}")
    conn.rollback()

# =============================================================================
# 5. INSERTAR RELACIÓN TUTOR_PACIENTE
# =============================================================================
print("\n📊 5/6 - Insertando relación TUTOR_PACIENTE...")
try:
    df_tutor_paciente = pd.read_csv('/app/rellenar_bd/paciente_tutor.csv', sep=';')
    relaciones_insertadas = 0
    
    for _, row in df_tutor_paciente.iterrows():
        id_paciente = row['ID_MASCOTA']
        rut_tutor = row['RUT_TUTOR_CON_DATOS']
        
        if pd.notna(rut_tutor):
            rut_tutor = rut_tutor.lower()

            cur.execute("""
                INSERT INTO govet.tutor_paciente (id_paciente, rut)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
            """, (id_paciente, rut_tutor))
            relaciones_insertadas += 1

    conn.commit()
    print(f"   ✅ {relaciones_insertadas} relaciones procesadas")
except Exception as e:
    print(f"   ❌ Error insertando relaciones tutor-paciente: {e}")
    conn.rollback()

# =============================================================================
# 6. GENERAR CONSULTAS MÉDICAS
# =============================================================================
print("\n📊 6/6 - Generando CONSULTAS médicas...")

# Datos para generar consultas realistas
motivos_consulta = [
    "Control de rutina",
    "Vacunación anual",
    "Desparasitación",
    "Consulta por vómitos",
    "Consulta por diarrea",
    "Esterilización",
    "Control post-operatorio",
    "Limpieza dental",
    "Problemas dermatológicos",
    "Cojera o dolor articular",
    "Control de peso",
    "Problemas respiratorios",
    "Control geriátrico",
    "Consulta por apatía",
    "Control de embarazo",
    "Problemas oculares",
    "Problemas auditivos",
    "Herida o traumatismo",
    "Control de enfermedad crónica",
    "Segunda opinión"
]

diagnosticos_perros = [
    "Paciente sano - Control preventivo",
    "Gastroenteritis leve",
    "Dermatitis alérgica",
    "Otitis externa",
    "Displasia de cadera leve",
    "Obesidad - Plan nutricional",
    "Gingivitis",
    "Parásitos intestinales",
    "Artritis degenerativa",
    "Conjuntivitis",
    "Infección de vías urinarias",
    "Tos de las perreras",
    "Lipoma benigno",
    "Herida superficial",
    "Deshidratación leve"
]

diagnosticos_gatos = [
    "Paciente sano - Control preventivo",
    "Gastroenteritis leve",
    "Dermatitis por pulgas",
    "Otitis por ácaros",
    "Enfermedad renal crónica inicial",
    "Sobrepeso - Plan nutricional",
    "Gingivoestomatitis",
    "Parásitos intestinales",
    "Cistitis idiopática felina",
    "Conjuntivitis",
    "Hipertiroidismo leve",
    "Complejo respiratorio felino",
    "Lipidosis hepática",
    "Herida por pelea",
    "Deshidratación leve"
]

estados_pelaje = ["Normal", "Opaco", "Brillante", "Reseco", "Graso", "Con caspa", "Irregular"]
condiciones_corporales = ["1/5 - Caquéctico", "2/5 - Delgado", "3/5 - Ideal", "4/5 - Sobrepeso", "5/5 - Obeso"]
mucosas = ["Rosadas", "Pálidas", "Congestivas", "Ictéricas", "Cianóticas"]
dht_estados = [0, 1, 2] # 0: normal, 1: leve, 2: moderada
nodulos_estados = ["Normales", "Aumentados", "Dolorosos", "No palpables"]
auscultacion = ["Normal", "Soplo grado I/VI", "Soplo grado II/VI", "Frecuencia aumentada", "Frecuencia disminuida", "Crepitaciones leves"]

# Generar fecha aleatoria entre 2023 y 2024
def fecha_aleatoria():
    inicio = datetime(2023, 1, 1)
    fin = datetime(2024, 12, 31)
    delta = fin - inicio
    random_days = random.randint(0, delta.days)
    return inicio + timedelta(days=random_days)

try:
    # Obtener pacientes existentes con sus tutores
    cur.execute("""
        SELECT 
            p.id_paciente, 
            tp.rut,
            p.nombre as nombre_paciente,
            e.nombre_cientifico as especie
        FROM govet.paciente p
        INNER JOIN govet.tutor_paciente tp ON p.id_paciente = tp.id_paciente
        INNER JOIN govet.raza r ON p.id_raza = r.id_raza
        INNER JOIN govet.especie e ON r.id_especie = e.id_especie
        WHERE tp.rut IS NOT NULL
        LIMIT 100;
    """)
    pacientes = cur.fetchall()
    
    print(f"   Se encontraron {len(pacientes)} pacientes con tutores")
    
    # Generar consultas
    consultas_insertadas = 0
    for paciente in pacientes:
        id_paciente, rut, nombre_paciente, especie = paciente
        
        # Generar entre 1 y 4 consultas por paciente
        num_consultas = random.randint(1, 4)
        
        for _ in range(num_consultas):
            # Seleccionar diagnóstico según especie
            if "Canis" in especie:  # Perros
                diagnostico = random.choice(diagnosticos_perros)
            else:  # Gatos y otros
                diagnostico = random.choice(diagnosticos_gatos)
            
            # Peso aleatorio según especie
            if "Canis" in especie:
                peso = round(random.uniform(2.5, 45.0), 2)  # Perros: 2.5kg - 45kg
            else:
                peso = round(random.uniform(2.0, 8.0), 2)   # Gatos: 2kg - 8kg
            
            # Datos de la consulta
            motivo = random.choice(motivos_consulta)
            estado_pelaje = random.choice(estados_pelaje)
            condicion_corporal = random.choice(condiciones_corporales)
            mucosa = random.choice(mucosas)
            dht = random.choice(dht_estados)
            nodulos = random.choice(nodulos_estados)
            auscult = random.choice(auscultacion)
            fecha = fecha_aleatoria()
            
            # Observaciones aleatorias
            observaciones_opciones = [
                f"Paciente {nombre_paciente} acude a control. Se realizan recomendaciones generales.",
                f"Se indica tratamiento. Control en 7 días.",
                f"Se toman muestras para análisis de laboratorio.",
                f"Propietario refiere mejoría. Se continúa tratamiento.",
                f"Se administra medicación. Próximo control en 15 días.",
                f"Se realiza procedimiento sin complicaciones.",
                "Se entregan indicaciones por escrito al tutor.",
                "Paciente cooperador durante examen clínico.",
                "Se agenda cirugía programada.",
                None  # Algunas sin observaciones
            ]
            observacion = random.choice(observaciones_opciones)
            
            try:
                cur.execute("""
                    INSERT INTO govet.consulta (
                        id_paciente, 
                        rut, 
                        diagnostico, 
                        estado_pelaje, 
                        peso, 
                        condicion_corporal, 
                        mucosas, 
                        dht, 
                        nodulos_linfaticos, 
                        "auscultacion_cardiaca-toraxica", 
                        observaciones, 
                        fecha_consulta, 
                        motivo
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    id_paciente,
                    rut,
                    diagnostico,
                    estado_pelaje,
                    peso,
                    condicion_corporal,
                    mucosa,
                    dht,
                    nodulos,
                    auscult,
                    observacion,
                    fecha,
                    motivo
                ))
                consultas_insertadas += 1
            except Exception as e:
                # Silenciar errores individuales de consultas duplicadas
                pass
    
    conn.commit()
    print(f"   ✅ {consultas_insertadas} consultas generadas")
    
except Exception as e:
    print(f"   ❌ Error generando consultas: {e}")
    conn.rollback()

# =============================================================================
# 6. SINCRONIZAR SECUENCIAS
# =============================================================================
print("\n🔄 7/7 - Sincronizando secuencias de IDs...")
try:
    secuencias = {
        "especie": ("id_especie", "especie_id_especie_seq"),
        "raza": ("id_raza", "raza_id_raza_seq"),
        "paciente": ("id_paciente", "mascota_id_mascota_seq"),
        "tutor": ("rut", None), 
        "consulta": ("id_consulta", "consulta_id_consulta_seq"),
        "tratamiento": ("id_tratamiento", "tratamiento_id_tratamiento_seq"),
        "consulta_tratamiento": ("id_consulta_tratamiento", "consulta_tratamiento_id_aplicacion_seq")
    }
    
    for tabla, (pk, seq) in secuencias.items():
        if seq:
            cur.execute(f"SELECT MAX({pk}) FROM govet.{tabla}")
            max_id = cur.fetchone()[0]
            if max_id:
                cur.execute(f"SELECT setval('govet.{seq}', %s, true)", (max_id,))
                print(f"   ✅ Secuencia {seq} sincronizada en {max_id}")
    
    conn.commit()
except Exception as e:
    print(f"   ⚠️  Advertencia sincronizando secuencias: {e}")
    conn.rollback()

# =============================================================================
# RESUMEN FINAL
# =============================================================================
print("\n" + "="*60)
print("✅ PROCESO COMPLETADO EXITOSAMENTE")
print("="*60)

try:
    # Contar registros en la base de datos
    cur.execute("SELECT COUNT(*) FROM govet.especie")
    total_especies = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM govet.raza")
    total_razas = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM govet.tutor")
    total_tutores = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM govet.paciente")
    total_pacientes = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM govet.tutor_paciente")
    total_relaciones = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM govet.consulta")
    total_consultas = cur.fetchone()[0]
    
    print(f"\n📊 Estado final de la base de datos:")
    print(f"   - Especies: {total_especies}")
    print(f"   - Razas: {total_razas}")
    print(f"   - Tutores: {total_tutores}")
    print(f"   - Pacientes: {total_pacientes}")
    print(f"   - Relaciones Tutor-Paciente: {total_relaciones}")
    print(f"   - Consultas: {total_consultas}")
    
except Exception as e:
    print(f"⚠️  Error obteniendo estadísticas finales: {e}")

# Cerrar conexión
cur.close()
conn.close()
print("\n🔒 Conexión cerrada")
