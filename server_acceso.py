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
# Esto le dice a Python que busque las carpetas 'modules' y 'database' 
# en la raíz del proyecto en el servidor.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# PARCHE PARA AUDITORIA (Agregado para que el servidor arranque)
# ============================================================
# Cuando el archivo 'autorizaciones_service.py' intente importar 
# 'AuditoriaService', lo encontrará aquí y no fallará.
class AuditoriaService:
    def __init__(self):
        pass
    def registrar_log(self, *args, **kwargs):
        pass
# ============================================================

app = Flask(__name__)
service = AutorizacionesService()

# ============================================================
# PÁGINA PRINCIPAL - REDIRECCIÓN
# ============================================================

@app.route('/')
def index():
    return """
    <h1>🏠 Sistema de Autorización de Acceso</h1>
    <p>Bienvenido al sistema de gestión de accesos.</p>
    <ul>
        <li><a href="/titular">🔑 Portal del Titular (generar QR)</a></li>
        <li><a href="/portero">🛡️ Portal del Portero (escanear QR)</a></li>
    </ul>
    """

# ============================================================
# PORTAL DEL TITULAR (Generar QR)
# ============================================================

@app.route('/titular', methods=['GET', 'POST'])
def portal_titular():
    if request.method == 'POST':
        # Procesar formulario
        data = {
            'id_cta': request.form.get('id_cta'),
            'id_titular': request.form.get('id_titular'),
            'visitante_nombre': request.form.get('visitante_nombre'),
            'visitante_dni': request.form.get('visitante_dni'),
            'visitante_telefono': request.form.get('visitante_telefono'),
            'visitante_vehiculo': request.form.get('visitante_vehiculo'),
            'fecha_ingreso': request.form.get('fecha_ingreso'),
            'hora_ingreso': request.form.get('hora_ingreso'),
            'fecha_egreso': request.form.get('fecha_egreso'),
            'hora_egreso': request.form.get('hora_egreso'),
            'motivo': request.form.get('motivo'),
            'relacion': request.form.get('relacion')
        }
        
        usuario = {'nombre': request.form.get('usuario_creacion', 'Titular')}
        
        try:
            resultado = service.crear_autorizacion(data, usuario)
            
            # Mostrar resultado con QR
            return render_template_string(RESULTADO_QR_HTML, **resultado)
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # GET: Mostrar formulario
    return render_template_string(FORMULARIO_TITULAR_HTML)

# ============================================================
# PORTAL DEL PORTERO (Escaneo QR)
# ============================================================

@app.route('/acceso')
def acceso_portero():
    token = request.args.get('token')
    
    if not token:
        return "❌ No se proporcionó token de acceso"
    
    # Validar token
    autorizacion = service.validar_token(token)
    
    if not autorizacion:
        return render_template_string(ERROR_TOKEN_HTML, mensaje="❌ Token inválido o autorización revocada")
    
    return render_template_string(VALIDACION_QR_HTML, **autorizacion)

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
    
    # Contar estadísticas
    total = len(historial)
    activos = sum(1 for r in historial if r.get('estado') == 'Activa')
    dentro = sum(1 for r in historial if r.get('estado_acceso') == 'Dentro')
    
    return render_template_string(DASHBOARD_HTML, 
                                   total=total, 
                                   activos=activos, 
                                   dentro=dentro,
                                   historial=historial)

# ============================================================
# TEMPLATES HTML
# ============================================================

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
    </style>
</head>
<body>
    <div class="container">
        <h1>🔑 Autorizar Acceso</h1>
        <p>Complete los datos del visitante para generar un QR de acceso.</p>
        
        <form method="POST">
            <input type="hidden" name="id_cta" value="1">
            <input type="hidden" name="id_titular" value="1">
            <input type="hidden" name="usuario_creacion" value="Titular">
            
            <label>👤 Nombre del visitante *</label>
            <input type="text" name="visitante_nombre" required>
            
            <label>📄 DNI del visitante *</label>
            <input type="text" name="visitante_dni" required>
            
            <label>📱 Teléfono del visitante</label>
            <input type="text" name="visitante_telefono">
            
            <label>🚗 Vehículo (opcional)</label>
            <input type="text" name="visitante_vehiculo">
            
            <label>📅 Fecha de ingreso *</label>
            <input type="date" name="fecha_ingreso" required>
            
            <label>🕒 Hora de ingreso *</label>
            <input type="time" name="hora_ingreso" required>
            
            <label>📅 Fecha de egreso *</label>
            <input type="date" name="fecha_egreso" required>
            
            <label>🕒 Hora de egreso *</label>
            <input type="time" name="hora_egreso" required>
            
            <label>📌 Motivo</label>
            <input type="text" name="motivo" placeholder="Visita familiar, mantenimiento, etc.">
            
            <label>🤝 Relación con el visitante</label>
            <select name="relacion">
                <option value="Familiar">Familiar</option>
                <option value="Amigo">Amigo</option>
                <option value="Trabajador">Trabajador</option>
                <option value="Contratista">Contratista</option>
                <option value="Otro">Otro</option>
            </select>
            
            <button type="submit" class="btn">✅ Generar QR</button>
        </form>
    </div>
</body>
</html>
"""

RESULTADO_QR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>✅ QR Generado</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; text-align: center; }
        .qr-img { border: 2px solid #ddd; border-radius: 10px; padding: 20px; margin: 20px auto; display: inline-block; }
        .btn { background: #27ae60; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
        .btn-blue { background: #3498db; }
        .info { text-align: left; background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .token { font-family: monospace; background: #ecf0f1; padding: 10px; border-radius: 5px; word-break: break-all; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ QR Generado con Éxito</h1>
        
        <!-- CORRECCIÓN: La imagen ahora usa el texto Base64, no un archivo -->
        <div class="qr-img">
            <img src="{{ qr_base64 }}" width="250" height="250" alt="QR">
        </div>
        
        <div class="info">
            <p><strong>👤 Visitante:</strong> {{ visitante_nombre }}</p>
            <p><strong>📄 DNI:</strong> {{ visitante_dni }}</p>
            <p><strong>📅 Vigencia:</strong> {{ fecha_ingreso_autorizada }} {{ hora_ingreso_autorizada }} - {{ fecha_egreso_autorizada }} {{ hora_egreso_autorizada }}</p>
            <p><strong>🔑 Token:</strong> <span class="token">{{ token }}</span></p>
            <p><strong>🔗 Enlace:</strong> <span class="token">{{ url }}</span></p>
        </div>
        
        <div>
            <button class="btn btn-blue" onclick="copiarEnlace()">📋 Copiar Enlace</button>
        </div>
        <br>
        <a href="/titular" class="btn">🔙 Nueva Autorización</a>
        <a href="/" class="btn btn-blue">🏠 Inicio</a>
    </div>
    
    <script>
        function copiarEnlace() {
            const enlace = "{{ url }}";
            navigator.clipboard.writeText(enlace);
            alert("✅ Enlace copiado al portapapeles");
        }
    </script>
</body>
</html>
"""

VALIDACION_QR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>✅ Validación de QR</title>
    <style>
        body { font-family: Arial; background: #f0f2f5; padding: 20px; }
        .container { max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; }
        .valid { color: #27ae60; }
        .invalid { color: #e74c3c; }
        .pending { color: #f39c12; }
        .info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .btn { background: #27ae60; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        .btn-red { background: #e74c3c; }
        .btn-blue { background: #3498db; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{% if estado_verificacion == 'Valida' %}✅ Acceso Autorizado{% elif estado_verificacion == 'Pendiente' %}⏳ Autorización Pendiente{% elif estado_verificacion == 'Vencida' %}❌ Autorización Vencida{% else %}⚠️ Estado Desconocido{% endif %}</h1>
        
        <div class="info">
            <p><strong>👤 Visitante:</strong> {{ visitante_nombre }}</p>
            <p><strong>📄 DNI:</strong> {{ visitante_dni }}</p>
            <p><strong>🏠 Propiedad:</strong> CTA-{{ codigo_cta }} - {{ titular_nombre }}</p>
            <p><strong>📅 Vigencia:</strong> {{ fecha_ingreso_autorizada }} {{ hora_ingreso_autorizada }} - {{ fecha_egreso_autorizada }} {{ hora_egreso_autorizada }}</p>
            <p><strong>📌 Motivo:</strong> {{ motivo or 'No especificado' }}</p>
            <p><strong>🚗 Vehículo:</strong> {{ visitante_vehiculo or 'No registrado' }}</p>
            <p><strong>📊 Estado:</strong> 
                <span class="{% if estado_verificacion == 'Valida' %}valid{% elif estado_verificacion == 'Pendiente' %}pending{% else %}invalid{% endif %}">
                    {{ mensaje }}
                </span>
            </p>
        </div>
        
        <div>
            {% if estado_verificacion == 'Valida' %}
                <button class="btn" id="btnIngreso" onclick="registrarIngreso({{ id }})">✅ Registrar Ingreso</button>
                <button class="btn btn-red" id="btnEgreso" onclick="registrarEgreso({{ id }})" disabled>🚪 Registrar Egreso</button>
            {% else %}
                <button class="btn" disabled>⛔ Acceso Denegado</button>
            {% endif %}
        </div>
        <br>
        <a href="/portero" class="btn btn-blue">🔄 Escanear otro QR</a>
        <a href="/" class="btn btn-blue">🏠 Inicio</a>
    </div>
    
    <script>
        let idAutorizacion = {{ id }};
        let idRegistro = null;
        
        function registrarIngreso(id) {
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
                    alert(data.mensaje);
                    document.getElementById('btnIngreso').disabled = true;
                    document.getElementById('btnEgreso').disabled = false;
                    idRegistro = data.id_registro;
                } else {
                    alert('❌ Error: ' + data.mensaje);
                }
            })
            .catch(error => alert('❌ Error de conexión: ' + error));
        }
        
        function registrarEgreso() {
            if (!idRegistro) {
                alert('⚠️ Primero debe registrar el ingreso');
                return;
            }
            
            fetch('/registrar_egreso', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    id_registro: idRegistro,
                    portero: 'Portero'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.mensaje);
                    document.getElementById('btnEgreso').disabled = true;
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
            <div class="card">
                <div class="card-number">{{ total }}</div>
                <div class="card-title">Total Autorizaciones</div>
            </div>
            <div class="card">
                <div class="card-number">{{ activos }}</div>
                <div class="card-title">Activas</div>
            </div>
            <div class="card">
                <div class="card-number">{{ dentro }}</div>
                <div class="card-title">Dentro del predio</div>
            </div>
        </div>
        
        <h2>📋 Últimos Accesos</h2>
        <table>
            <thead>
                <tr>
                    <th>Visitante</th>
                    <th>Propiedad</th>
                    <th>Estado</th>
                    <th>Ingreso</th>
                    <th>Egreso</th>
                </tr>
            </thead>
            <tbody>
                {% for r in historial %}
                <tr>
                    <td>{{ r.visitante_nombre }}</td>
                    <td>CTA-{{ r.codigo_cta }}</td>
                    <td>
                        {% if r.estado_acceso == 'Dentro' %}
                            <span style="color: #27ae60;">✅ Dentro</span>
                        {% elif r.estado_acceso == 'Finalizado' %}
                            <span style="color: #7f8c8d;">⬜ Finalizado</span>
                        {% else %}
                            <span style="color: #f39c12;">⏳ Pendiente</span>
                        {% endif %}
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
# RUTA PARA SERVIR IMÁGENES QR (CORREGIDA PARA RENDER)
# ============================================================

@app.route('/static/qr/<filename>')
def serve_qr(filename):
    # CORRECCIÓN: Ya no usa rutas de Windows (C:\...). 
    # Ahora usa una ruta relativa que funciona en Render.
    ruta = os.path.join(app.root_path, "static", "qr", filename)
    
    if os.path.exists(ruta):
        return send_file(ruta, mimetype='image/png')
    
    # Si no encuentra la imagen, muestra un error visual en lugar de crashear el servidor
    return """
    <div style='text-align:center; font-family:Arial; margin-top:50px;'>
        <h1 style='color:#e74c3c;'>❌ Imagen no encontrada</h1>
        <p>El archivo <strong>{}</strong> no existe en la carpeta <strong>static/qr/</strong> del servidor.</p>
        <p>Sube la imagen a GitHub o crea la carpeta en Render.</p>
        <a href='/' style='background:#3498db; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;'>Volver al inicio</a>
    </div>
    """.format(filename), 404

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
    print("   • /acceso?token=xxx  → Validar token")
    print("   • /dashboard_acceso → Estadísticas")
    print("=" * 60)
    
    # Render usa el puerto 10000 por defecto en sus planes gratuitos, 
    # pero Gunicorn lo tomará de la variable de entorno, así que usamos 10000 o 5000.
    app.run(host='0.0.0.0', port=10000, debug=False)