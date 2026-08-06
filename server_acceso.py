# server_acceso.py
# Servidor web para el sistema de Autorización de Acceso con QR

from flask import Flask, render_template_string, request, jsonify, send_file
import sqlite3
from datetime import datetime
from modules.services.autorizaciones_service import AutorizacionesService
from database.db import get_connection
import os
import sys 

# CORRECCIÓN IMPORTANTE PARA RENDER:
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# PARCHE PARA AUDITORIA
# ============================================================
class AuditoriaService:
    def __init__(self):
        pass
    def registrar_log(self, *args, **kwargs):
        pass
# ============================================================

app = Flask(__name__)
service = AutorizacionesService()

# ============================================================
# CORRECCIÓN FINAL: CREAR LA BASE DE DATOS AUTOMÁTICAMENTE
# ============================================================
def inicializar_base_datos():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS titulares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cta TEXT UNIQUE,
                apellido_nombre TEXT,
                email TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS autorizaciones_acceso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cta TEXT,
                id_titular INTEGER,
                visitante_nombre TEXT,
                visitante_dni TEXT,
                visitante_telefono TEXT,
                visitante_vehiculo TEXT,
                fecha_ingreso_autorizada TEXT,
                hora_ingreso_autorizada TEXT,
                fecha_egreso_autorizada TEXT,
                hora_egreso_autorizada TEXT,
                motivo TEXT,
                relacion TEXT,
                qr_code TEXT,
                token TEXT UNIQUE,
                estado TEXT,
                fecha_creacion TEXT,
                fecha_revocacion TEXT,
                motivo_revocacion TEXT,
                usuario_creacion TEXT,
                FOREIGN KEY(id_titular) REFERENCES titulares(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registros_acceso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_autorizacion INTEGER,
                fecha_ingreso TEXT,
                hora_ingreso TEXT,
                portero_ingreso TEXT,
                fecha_egreso TEXT,
                hora_egreso TEXT,
                portero_egreso TEXT,
                FOREIGN KEY(id_autorizacion) REFERENCES autorizaciones_acceso(id)
            )
        ''')
        
        cursor.execute("SELECT count(*) FROM titulares")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO titulares (id_cta, apellido_nombre, email) 
                VALUES (?, ?, ?)
            ''', ("CTA-001", "Titular de Prueba", "test@test.com"))
            
        conn.commit()
        conn.close()
        print("✅ Base de datos inicializada correctamente en Render.")
        
    except Exception as e:
        print(f"⚠️ Error al inicializar la base de datos: {e}")

inicializar_base_datos()
# ============================================================


# ============================================================
# TEMPLATES HTML DEFINIDOS PRIMERO
# ============================================================

RESULTADO_QR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>✅ QR Generado</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; text-align: center; }
        .qr-img { border: 2px solid #ddd; border-radius: 10px; padding: 20px; margin: 20px auto; display: inline-block; }
        .btn { padding: 12px 20px; border: none; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; font-size: 15px; font-weight: bold; color: white; width: 100%; box-sizing: border-box; }
        .btn-wa { background: #25D366; }
        .btn-blue { background: #3498db; }
        .btn-volver { background: #27ae60; }
        .info { text-align: left; background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .token-box { font-family: monospace; background: #ecf0f1; padding: 10px; border-radius: 5px; word-break: break-all; font-size: 13px; display: block; }
        .action-buttons { display: flex; flex-direction: column; gap: 10px; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ QR Generado con Éxito</h1>
        
        <div class="qr-img">
            <img src="{{ qr_base64 }}" width="250" height="250" alt="QR">
        </div>
        
        <div class="info">
            <p><strong>👤 Visitante:</strong> {{ visitante_nombre }}</p>
            <p><strong>📄 DNI:</strong> {{ visitante_dni }}</p>
            <p><strong>📅 Vigencia:</strong> {{ fecha_ingreso_autorizada }} {{ hora_ingreso_autorizada }} - {{ fecha_egreso_autorizada }} {{ hora_egreso_autorizada }}</p>
            <p><strong>🔑 Token:</strong> <span class="token-box">{{ token }}</span></p>
        </div>
        
        <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 20px;">
            <h3 style="color: #555; font-size: 16px; margin-bottom: 15px;">📲 Notificaciones Inteligentes</h3>
            
            <div class="action-buttons">
                <!-- ÚNICO BOTÓN: Envía al Visitante y al Portero al mismo tiempo -->
                <button class="btn btn-wa" onclick="enviarNotificaciones()">📲 Enviar Notificaciones</button>
            </div>
        </div>
        
        <br>
        <a href="/titular" class="btn btn-volver">🔙 Nueva Autorización</a>
        <a href="/" class="btn btn-blue">🏠 Inicio</a>
    </div>
    
    <script>
        const enlaceCompleto = "{{ url }}";
        const token = "{{ token }}";
        const nombre = "{{ visitante_nombre }}";
        const dni = "{{ visitante_dni }}";
        
        const telVisitante = "{{ telefono_visitante }}";
        const telPortero = "{{ telefono_portero }}";
        
        function enviarNotificaciones() {
            // 1. Abrir WhatsApp al Visitante
            if (telVisitante) {
                const msgVisitante = `Hola ${nombre}! Aquí tienes tu enlace de acceso al condominio. Por favor, preséntaselo al portero cuando llegues: ${enlaceCompleto}`;
                const urlVisitante = `https://wa.me/${telVisitante}?text=${encodeURIComponent(msgVisitante)}`;
                window.open(urlVisitante, '_blank');
            } else {
                alert("⚠️ No cargaste el teléfono del visitante.");
            }

            // 2. Abrir WhatsApp al Portero (en una pestaña separada)
            if (telPortero) {
                const msgPortero = `🚨 NUEVO ACCESO PARA VALIDAR\\n\\n👤 Visitante: ${nombre}\\n📄 DNI: ${dni}\\n🔑 Token: ${token}\\n\\n👉 Ingrese el token en el sistema.`;
                const urlPortero = `https://wa.me/${telPortero}?text=${encodeURIComponent(msgPortero)}`;
                
                // Pequeño retraso para no saturar el navegador al abrir dos pestañas
                setTimeout(() => {
                    window.open(urlPortero, '_blank');
                }, 500);
            } else {
                alert("⚠️ No cargaste el teléfono del portero.");
            }
        }
    </script>
</body>
</html>
"""

FORMULARIO_TITULAR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🔑 Autorizar Acceso</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; }
        label { display: block; margin-top: 10px; font-weight: bold; }
        input, select { width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; }
        .btn { background: #27ae60; color: white; padding: 12px; border: none; border-radius: 4px; cursor: pointer; width: 100%; margin-top: 20px; }
        .btn:hover { background: #2ecc71; }
        h1 { color: #2c3e50; }
        .section-title { margin-top: 20px; border-top: 1px solid #eee; padding-top: 15px; color: #555; font-size: 14px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔑 Autorizar Acceso</h1>
        <p>Complete los datos del visitante para generar un QR de acceso.</p>
        
        {% if error %}
        <div style="background-color: #ffebee; color: #c62828; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #ef9a9a;">
            {{ error }}
        </div>
        {% endif %}
        
        <form method="POST">
            <input type="hidden" name="id_cta" value="CTA-001">
            <input type="hidden" name="id_titular" value="1">
            <input type="hidden" name="usuario_creacion" value="Titular">
            
            <label>👤 Nombre del visitante *</label>
            <input type="text" name="visitante_nombre" value="{{ request.form.get('visitante_nombre', '') }}" required>
            
            <label>📄 DNI del visitante *</label>
            <input type="text" name="visitante_dni" value="{{ request.form.get('visitante_dni', '') }}" required>
            
            <label>📱 Teléfono del visitante</label>
            <input type="text" name="telefono_visitante" value="{{ request.form.get('telefono_visitante', '') }}" placeholder="Ej: +5491112345678">
            
            <label>🚗 Vehículo (opcional)</label>
            <input type="text" name="visitante_vehiculo" value="{{ request.form.get('visitante_vehiculo', '') }}">
            
            <div class="section-title">📅 Fechas y Horarios</div>
            <label>Fecha de ingreso *</label>
            <input type="date" name="fecha_ingreso" value="{{ request.form.get('fecha_ingreso', '') }}" required>
            
            <label>Hora de ingreso *</label>
            <input type="time" name="hora_ingreso" value="{{ request.form.get('hora_ingreso', '') }}" required>
            
            <label>Fecha de egreso *</label>
            <input type="date" name="fecha_egreso" value="{{ request.form.get('fecha_egreso', '') }}" required>
            
            <label>Hora de egreso *</label>
            <input type="time" name="hora_egreso" value="{{ request.form.get('hora_egreso', '') }}" required>
            
            <div class="section-title">📲 Envío de Avisos</div>
            <label>Teléfono del Portero</label>
            <input type="text" name="telefono_portero" value="{{ request.form.get('telefono_portero', '') }}" placeholder="Ej: +5491155667788">
            
            <label>📌 Motivo</label>
            <input type="text" name="motivo" value="{{ request.form.get('motivo', '') }}" placeholder="Visita familiar, mantenimiento, etc.">
            
            <label>🤝 Relación con el visitante</label>
            <select name="relacion">
                <option value="Familiar" {% if request.form.get('relacion') == 'Familiar' %}selected{% endif %}>Familiar</option>
                <option value="Amigo" {% if request.form.get('relacion') == 'Amigo' %}selected{% endif %}>Amigo</option>
                <option value="Trabajador" {% if request.form.get('relacion') == 'Trabajador' %}selected{% endif %}>Trabajador</option>
                <option value="Contratista" {% if request.form.get('relacion') == 'Contratista' %}selected{% endif %}>Contratista</option>
                <option value="Otro" {% if request.form.get('relacion') == 'Otro' %}selected{% endif %}>Otro</option>
            </select>
            
            <button type="submit" class="btn">✅ Generar QR</button>
        </form>
    </div>
</body>
</html>
"""

VALIDACION_QR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>✅ Validación de QR</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; }
        .valid { color: #27ae60; }
        .invalid { color: #e74c3c; }
        .pending { color: #f39c12; }
        .info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .input-group { margin-top: 15px; text-align: center; }
        input[type="text"] { padding: 10px; border: 2px solid #ddd; border-radius: 5px; width: 80%; max-width: 200px; font-size: 16px; text-align: center; }
        input[type="text"]:focus { border-color: #2196F3; outline: none; }
        .btn { background: #27ae60; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-red { background: #e74c3c; }
        .btn-blue { background: #3498db; }
        .btn-verify { background: #2196F3; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container" id="mainContainer">
        <h1 id="statusTitle">⏳ Verificando...</h1>
        
        <div class="info">
            <p><strong>👤 Visitante:</strong> {{ visitante_nombre }}</p>
            <p><strong>📄 DNI Registrado:</strong> {{ visitante_dni }}</p>
            <p><strong>🏠 Propiedad:</strong> CTA-{{ codigo_cta }} - {{ titular_nombre }}</p>
            <p><strong>📅 Vigencia:</strong> {{ fecha_ingreso_autorizada }} {{ hora_ingreso_autorizada }} - {{ fecha_egreso_autorizada }} {{ hora_egreso_autorizada }}</p>
            <p><strong>📌 Motivo:</strong> {{ motivo or 'No especificado' }}</p>
            <p><strong>📊 Estado del sistema:</strong> <span id="statusMessage" style="font-weight: bold; color: #f39c12;">⏳ Validando horario local...</span></p>
        </div>
        
        <div id="verificationSection" style="display: none;">
            <p style="font-weight: bold; color: #555;">🔒 Verificación de Seguridad</p>
            <p>Pregunte al visitante su número de DNI para confirmar su identidad.</p>
            <div class="input-group">
                <input type="text" id="dniInput" placeholder="Ingrese DNI del visitante" autocomplete="off">
                <br>
                <button class="btn btn-verify" id="btnVerify" onclick="verificarYRegistrar({{ id }}, '{{ visitante_dni }}')">🔍 Verificar y Registrar Ingreso</button>
            </div>
            <div id="resultMessage" style="margin-top: 10px; font-weight: bold;"></div>
        </div>
        
        <div id="deniedSection" style="display: none;">
            <button class="btn" disabled>⛔ Acceso Denegado</button>
        </div>

        <br><br>
        <a href="/portero" class="btn btn-blue">🔄 Escanear otro QR</a>
        <a href="/" class="btn btn-blue">🏠 Inicio</a>
    </div>
    
    <script>
        const fechaIngresoStr = "{{ fecha_ingreso_autorizada }} {{ hora_ingreso_autorizada }}";
        const fechaEgresoStr = "{{ fecha_egreso_autorizada }} {{ hora_egreso_autorizada }}";

        const fechaIngreso = new Date(fechaIngresoStr.replace(' ', 'T'));
        const fechaEgreso = new Date(fechaEgresoStr.replace(' ', 'T'));
        const ahora = new Date();

        const statusMessage = document.getElementById('statusMessage');
        const statusTitle = document.getElementById('statusTitle');
        const verificationSection = document.getElementById('verificationSection');
        const deniedSection = document.getElementById('deniedSection');

        if (ahora < fechaIngreso) {
            statusTitle.innerHTML = '⏳ Autorización Pendiente';
            statusMessage.innerHTML = '<span style="color: #f39c12;">⏳ La autorización aún no está vigente (según tu celular).</span>';
            deniedSection.style.display = 'block';
        } else if (ahora > fechaEgreso) {
            statusTitle.innerHTML = '❌ Autorización Vencida';
            statusMessage.innerHTML = '<span style="color: #e74c3c;">⚠️ La autorización ha vencido (según tu celular).</span>';
            deniedSection.style.display = 'block';
        } else {
            statusTitle.innerHTML = '✅ Acceso Autorizado';
            statusMessage.innerHTML = '<span style="color: #27ae60;">✅ Autorización válida en este momento.</span>';
            verificationSection.style.display = 'block';
        }

        let idRegistro = null;

        function verificarYRegistrar(id, dniCorrecto) {
            const dniIngresado = document.getElementById('dniInput').value.trim();
            const mensajeDiv = document.getElementById('resultMessage');

            if (dniIngresado === '') {
                mensajeDiv.innerHTML = '<span style="color: #f39c12;">⚠️ Por favor, ingrese el DNI.</span>';
                return;
            }

            if (dniIngresado !== dniCorrecto) {
                mensajeDiv.innerHTML = '<span style="color: #e74c3c;">❌ DNI INCORRECTO. No se puede registrar el ingreso.</span>';
                document.getElementById('dniInput').value = '';
                return;
            }

            mensajeDiv.innerHTML = '<span style="color: #27ae60;">✅ DNI Verificado. Registrando ingreso...</span>';
            document.getElementById('btnVerify').disabled = true;

            fetch('/registrar_ingreso', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id_autorizacion: id,
                    portero: 'Portero'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    mensajeDiv.innerHTML = '<span style="color: #27ae60;">✅ ' + data.mensaje + '</span>';
                    document.getElementById('verificationSection').innerHTML = '<h2 style="color: #27ae60;">✅ Ingreso Registrado</h2><p>El visitante ha ingresado correctamente.</p><button class="btn btn-red" onclick="registrarEgreso(' + data.id_registro + ')">🚪 Registrar Egreso</button>';
                    idRegistro = data.id_registro;
                } else {
                    mensajeDiv.innerHTML = '<span style="color: #e74c3c;">❌ Error: ' + data.mensaje + '</span>';
                }
            })
            .catch(error => {
                mensajeDiv.innerHTML = '<span style="color: #e74c3c;">❌ Error de conexión: ' + error + '</span>';
            });
        }

        function registrarEgreso(id) {
            if (!id) return;
            fetch('/registrar_egreso', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id_registro: id,
                    portero: 'Portero'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.mensaje);
                    document.getElementById('verificationSection').innerHTML = '<h2 style="color: #7f8c8d;">⬜ Egreso Registrado</h2>';
                } else {
                    alert('❌ Error: ' + data.mensaje);
                }
            })
            .catch(error => alert('❌ Error de conexión: ' + error));
        }
    </script>
</body>
</html>
"""

ERROR_TOKEN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>❌ Acceso Denegado</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .container { max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px; text-align: center; }
        .invalid { color: #e74c3c; }
        .btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="invalid">❌ Acceso Denegado</h1>
        <p>{{ mensaje }}</p>
        <br>
        <a href="/portero" class="btn">🔄 Escanear otro QR</a>
        <a href="/" class="btn">🏠 Inicio</a>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>📊 Dashboard de Accesos</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .container { max-width: 1200px; margin: auto; }
        .card { background: white; padding: 20px; border-radius: 10px; margin: 10px; display: inline-block; min-width: 150px; }
        .card-number { font-size: 36px; font-weight: bold; }
        .card-title { color: #7f8c8d; }
        table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; margin-top: 20px; }
        th { background: #2c3e50; color: white; padding: 10px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ecf0f1; }
        .btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Dashboard de Accesos</h1>
        <div>
            <div class="card"><div class="card-number">{{ total }}</div><div class="card-title">Total Autorizaciones</div></div>
            <div class="card"><div class="card-number">{{ activos }}</div><div class="card-title">Activas</div></div>
            <div class="card"><div class="card-number">{{ dentro }}</div><div class="card-title">Dentro del predio</div></div>
        </div>
        <h2>📋 Últimos Accesos</h2>
        <table>
            <thead><tr><th>Visitante</th><th>Propiedad</th><th>Estado</th><th>Ingreso</th><th>Egreso</th></tr></thead>
            <tbody>
                {% for r in historial %}
                <tr>
                    <td>{{ r.visitante_nombre }}</td>
                    <td>CTA-{{ r.codigo_cta }}</td>
                    <td>
                        {% if r.estado_acceso == 'Dentro' %}<span style="color: #27ae60;">✅ Dentro</span>
                        {% elif r.estado_acceso == 'Finalizado' %}<span style="color: #7f8c8d;">⬜ Finalizado</span>
                        {% else %}<span style="color: #f39c12;">⏳ Pendiente</span>{% endif %}
                    </td>
                    <td>{{ r.fecha_ingreso or '-' }} {{ r.hora_ingreso or '' }}</td>
                    <td>{{ r.fecha_egreso or '-' }} {{ r.hora_egreso or '' }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <br>
        <a href="/" class="btn">🏠 Inicio</a>
    </div>
</body>
</html>
"""


# ============================================================
# PÁGINA PRINCIPAL - DISEÑO ESTILO APP PROFESIONAL
# ============================================================
@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sistema de Acceso</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); margin: 0; height: 100vh; display: flex; justify-content: center; align-items: center; }
            .card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); text-align: center; width: 90%; max-width: 400px; }
            h1 { color: #333; margin-bottom: 20px; font-size: 24px; }
            .menu { display: flex; flex-direction: column; gap: 15px; margin-top: 20px; }
            .btn { display: block; padding: 15px; text-decoration: none; border-radius: 10px; font-weight: bold; transition: transform 0.2s; }
            .btn:hover { transform: scale(1.02); }
            .btn-titular { background: #4CAF50; color: white; }
            .btn-portero { background: #2196F3; color: white; }
            .footer { margin-top: 20px; font-size: 12px; color: #888; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🏠 Sistema de Acceso</h1>
            <p>Selecciona tu rol para continuar:</p>
            <div class="menu">
                <a href="/titular" class="btn btn-titular">🔑 Portal del Titular</a>
                <a href="/portero" class="btn btn-portero">🛡️ Portal del Portero</a>
            </div>
            <div class="footer">Sistema de Autorización de Acceso con QR</div>
        </div>
    </body>
    </html>
    """


# ============================================================
# PORTAL DEL PORTERO - NUEVA PÁGINA CON BUSCADOR
# ============================================================
@app.route('/portero')
def portal_portero():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🛡️ Portal del Portero</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #e9ecef; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
            .container { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center; width: 90%; max-width: 450px; }
            h1 { color: #2196F3; }
            p { color: #555; margin-bottom: 20px; }
            .input-group { display: flex; flex-direction: column; gap: 15px; }
            textarea { 
                padding: 15px; border: 2px solid #dee2e6; border-radius: 10px; font-size: 16px; width: 100%; box-sizing: border-box; resize: none; height: 100px;
                font-family: monospace;
            }
            textarea:focus { border-color: #2196F3; outline: none; }
            .btn { padding: 15px; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; color: white; cursor: pointer; width: 100%; text-decoration: none; display: inline-block; box-sizing: border-box; }
            .btn-validar { background: #2196F3; }
            .btn-validar:hover { background: #1976D2; }
            .btn-volver { background: #6c757d; margin-top: 15px; }
            .btn-volver:hover { background: #5a6268; }
            .instruccion { font-size: 13px; color: #6c757d; margin: 10px 0; text-align: left; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ Portal del Portero</h1>
            <p>Escriba aquí el TOKEN o el ENLACE que el visitante le dicta en voz alta.</p>
            
            <div class="instruccion">💡 El visitante debe leerle el enlace que tiene en su celular.</div>
            
            <form action="/acceso" method="GET" class="input-group">
                <textarea name="token" placeholder="Ej: xxxxxx   o   https://sistema-acceso-uv-1.onrender.com/acceso?token=xxxxxx" required></textarea>
                <button type="submit" class="btn btn-validar">🔍 Validar Acceso</button>
            </form>
            
            <a href="/" class="btn btn-volver">🏠 Volver al inicio</a>
        </div>
    </body>
    </html>
    """


# ============================================================
# PORTAL DEL TITULAR (Generar QR)
# ============================================================
@app.route('/titular', methods=['GET', 'POST'])
def portal_titular():
    error = None  # Variable para guardar mensajes de error
    
    if request.method == 'POST':
        # Procesar formulario
        data = {
            'id_cta': request.form.get('id_cta'),
            'id_titular': request.form.get('id_titular'),
            'visitante_nombre': request.form.get('visitante_nombre'),
            'visitante_dni': request.form.get('visitante_dni'),
            'visitante_telefono': request.form.get('telefono_visitante'), # Guardamos el teléfono del visitante
            'visitante_vehiculo': request.form.get('visitante_vehiculo'),
            'fecha_ingreso': request.form.get('fecha_ingreso'),
            'hora_ingreso': request.form.get('hora_ingreso'),
            'fecha_egreso': request.form.get('fecha_egreso'),
            'hora_egreso': request.form.get('hora_egreso'),
            'motivo': request.form.get('motivo'),
            'relacion': request.form.get('relacion')
        }
        
        usuario = {'nombre': request.form.get('usuario_creacion', 'Titular')}
        
        # ============================================================
        # VALIDACIÓN DE FECHAS CORREGIDA (Solo verifica coherencia)
        # ============================================================
        try:
            fecha_ingreso_str = f"{data['fecha_ingreso']} {data['hora_ingreso']}"
            fecha_ingreso_dt = datetime.strptime(fecha_ingreso_str, "%Y-%m-%d %H:%M")
            
            fecha_egreso_str = f"{data['fecha_egreso']} {data['hora_egreso']}"
            fecha_egreso_dt = datetime.strptime(fecha_egreso_str, "%Y-%m-%d %H:%M")
            
            if fecha_egreso_dt <= fecha_ingreso_dt:
                error = "❌ Error: La fecha y hora de egreso deben ser posteriores a la fecha y hora de ingreso."
                
        except Exception as e:
            error = f"❌ Error de formato en las fechas: {str(e)}"
        # ============================================================
        
        if error is None:
            try:
                resultado = service.crear_autorizacion(data, usuario)
                
                # CORRECCIÓN FINAL: Pasamos absolutamente todos los datos
                return render_template_string(
                    RESULTADO_QR_HTML, 
                    **resultado,
                    visitante_nombre=request.form.get('visitante_nombre', ''),
                    visitante_dni=request.form.get('visitante_dni', ''),
                    fecha_ingreso_autorizada=request.form.get('fecha_ingreso', ''),
                    hora_ingreso_autorizada=request.form.get('hora_ingreso', ''),
                    fecha_egreso_autorizada=request.form.get('fecha_egreso', ''),
                    hora_egreso_autorizada=request.form.get('hora_egreso', ''),
                    telefono_visitante=request.form.get('telefono_visitante', ''),
                    telefono_portero=request.form.get('telefono_portero', '')
                )
            except Exception as e:
                error = f"❌ Error del sistema: {str(e)}"
    
    return render_template_string(FORMULARIO_TITULAR_HTML, error=error)


# ============================================================
# VALIDACIÓN DE ACCESO
# ============================================================
@app.route('/acceso')
def acceso_portero():
    token = request.args.get('token')
    
    if not token:
        return "❌ No se proporcionó token de acceso"
    
    if "token=" in token:
        token = token.split("token=")[-1].split("&")[0]
    
    autorizacion = service.validar_token(token)
    
    if not autorizacion:
        return render_template_string(ERROR_TOKEN_HTML, mensaje="❌ Token inválido o autorización revocada")
    
    return render_template_string(VALIDACION_QR_HTML, **autorizacion)


# ============================================================
# REGISTRO DE INGRESOS Y EGRESOS
# ============================================================
@app.route('/registrar_ingreso', methods=['POST'])
def registrar_ingreso():
    data = request.get_json()
    id_autorizacion = data.get('id_autorizacion')
    portero = data.get('portero', 'Portero')
    resultado = service.registrar_ingreso(id_autorizacion, portero)
    return jsonify(resultado)

@app.route('/registrar_egreso', methods=['POST'])
def registrar_egreso():
    data = request.get_json()
    id_registro = data.get('id_registro')
    portero = data.get('portero', 'Portero')
    resultado = service.registrar_egreso(id_registro, portero)
    return jsonify(resultado)


# ============================================================
# DASHBOARD DE ACCESOS
# ============================================================
@app.route('/dashboard_acceso')
def dashboard_acceso():
    historial = service.obtener_historial(limite=100)
    
    total = len(historial)
    activos = sum(1 for r in historial if r.get('estado') == 'Activa')
    dentro = sum(1 for r in historial if r.get('estado_acceso') == 'Dentro')
    
    return render_template_string(DASHBOARD_HTML, 
                                   total=total, 
                                   activos=activos, 
                                   dentro=dentro,
                                   historial=historial)


# ============================================================
# INICIO DEL SERVIDOR
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🏠 SISTEMA DE AUTORIZACIÓN DE ACCESO - QR")
    print("=" * 60)
    print("📌 Servidor iniciado en:")
    print("   • http://0.0.0.0:10000")
    print("=" * 60)
    print("📌 Accesos:")
    print("   • /titular  → Generar QR")
    print("   • /portero  → Portal para buscar y validar token")
    print("   • /acceso?token=xxx  → Validar token directo")
    print("   • /dashboard_acceso → Estadísticas")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=10000, debug=False)