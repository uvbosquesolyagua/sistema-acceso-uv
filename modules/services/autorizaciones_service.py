# modules/services/autorizaciones_service.py
# Servicio de Autorización de Acceso con QR (Versión Base64 sin disco)

import sqlite3
import secrets
import qrcode
import os
import io
import base64
from datetime import datetime, timedelta, timezone
from database.db import get_connection

# ============================================================
# PARCHE PARA AUDITORIA
# ============================================================
class AuditoriaService:
    def __init__(self):
        pass
    def registrar(self, *args, **kwargs):
        pass
# ============================================================

class AutorizacionesService:
    def __init__(self):
        self.auditoria = AuditoriaService()
    
    def generar_token(self):
        return secrets.token_urlsafe(32)
    
    def generar_qr_url(self, token, host="sistema-acceso-uv-1.onrender.com", port=80):
        return f"https://{host}/acceso?token={token}"
    
    def generar_qr_base64(self, url):
        img = qrcode.make(url)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
    
    def crear_autorizacion(self, data, usuario):
        token = self.generar_token()
        url = self.generar_qr_url(token)
        qr_base64 = self.generar_qr_base64(url)
        
        fecha_actual = datetime.now().isoformat()
        
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            INSERT INTO autorizaciones_acceso (
                id_cta, id_titular, visitante_nombre, visitante_dni,
                visitante_telefono, visitante_vehiculo,
                fecha_ingreso_autorizada, hora_ingreso_autorizada,
                fecha_egreso_autorizada, hora_egreso_autorizada,
                motivo, relacion,
                qr_code, token, estado, fecha_creacion, usuario_creacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Activa', ?, ?)
        """, (
            data['id_cta'],
            data['id_titular'],
            data['visitante_nombre'],
            data['visitante_dni'],
            data.get('visitante_telefono', ''),
            data.get('visitante_vehiculo', ''),
            data['fecha_ingreso'],
            data['hora_ingreso'],
            data['fecha_egreso'],
            data['hora_egreso'],
            data.get('motivo', ''),
            data.get('relacion', 'Familiar'),
            '',
            token,
            fecha_actual,
            usuario.get('nombre', 'Sistema')
        ))
        
        conn.commit()
        id_autorizacion = cursor.lastrowid
        conn.close()
        
        self.auditoria.registrar(
            usuario=usuario,
            modulo="autorizaciones",
            accion="crear_autorizacion",
            descripcion=f"Autorización para {data['visitante_nombre']}"
        )
        
        return {
            'id': id_autorizacion,
            'token': token,
            'url': url,
            'qr_base64': qr_base64
        }
    
    def validar_token(self, token):
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            
            autorizacion = conn.execute("""
                SELECT 
                    a.*,
                    t.apellido_nombre as titular_nombre,
                    t.id_cta as codigo_cta
                FROM autorizaciones_acceso a
                LEFT JOIN titulares t ON a.id_titular = t.id
                WHERE a.token = ? AND a.estado = 'Activa'
            """, (token,)).fetchone()
            
            conn.close()
            
            if not autorizacion:
                return None
            
            autorizacion = dict(autorizacion)
            
            # ============================================================
            # CORRECCIÓN FINAL DE ZONA HORARIA (UTC)
            # ============================================================
            # Para evitar problemas de zonas horarias, usamos UTC que es universal.
            ahora = datetime.now(timezone.utc)
            
            fecha_ingreso = datetime.strptime(
                f"{autorizacion['fecha_ingreso_autorizada']} {autorizacion['hora_ingreso_autorizada']}",
                "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc) # Forzamos a que estas fechas también sean UTC
            
            fecha_egreso = datetime.strptime(
                f"{autorizacion['fecha_egreso_autorizada']} {autorizacion['hora_egreso_autorizada']}",
                "%Y-%m-%d %H:%M"
            ).replace(tzinfo=timezone.utc) # Forzamos a que estas fechas también sean UTC
            
            if ahora < fecha_ingreso:
                autorizacion['estado_verificacion'] = 'Pendiente'
                autorizacion['mensaje'] = '⏳ La autorización aún no está vigente'
            elif ahora > fecha_egreso:
                autorizacion['estado_verificacion'] = 'Vencida'
                autorizacion['mensaje'] = '⚠️ La autorización ha vencido'
            else:
                autorizacion['estado_verificacion'] = 'Valida'
                autorizacion['mensaje'] = '✅ Autorización válida'
            # ============================================================
            
            return autorizacion
            
        except Exception as e:
            print(f"Error al validar token: {e}")
            return None
    
    def registrar_ingreso(self, id_autorizacion, portero):
        fecha_actual = datetime.now()
        
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        
        existe = conn.execute("""
            SELECT id FROM registros_acceso
            WHERE id_autorizacion = ? AND fecha_egreso IS NULL
        """, (id_autorizacion,)).fetchone()
        
        if existe:
            conn.close()
            return {'success': False, 'mensaje': 'El ingreso ya fue registrado'}
        
        cursor = conn.execute("""
            INSERT INTO registros_acceso (
                id_autorizacion, fecha_ingreso, hora_ingreso, portero_ingreso
            ) VALUES (?, ?, ?, ?)
        """, (
            id_autorizacion,
            fecha_actual.strftime("%Y-%m-%d"),
            fecha_actual.strftime("%H:%M"),
            portero
        ))
        
        conn.commit()
        id_registro = cursor.lastrowid
        conn.close()
        
        return {
            'success': True,
            'mensaje': '✅ Ingreso registrado correctamente',
            'id_registro': id_registro,
            'fecha_ingreso': fecha_actual.strftime("%Y-%m-%d %H:%M")
        }
    
    def registrar_egreso(self, id_registro, portero):
        fecha_actual = datetime.now()
        
        conn = get_connection()
        conn.execute("""
            UPDATE registros_acceso
            SET fecha_egreso = ?, hora_egreso = ?, portero_egreso = ?
            WHERE id = ?
        """, (
            fecha_actual.strftime("%Y-%m-%d"),
            fecha_actual.strftime("%H:%M"),
            portero,
            id_registro
        ))
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'mensaje': '✅ Egreso registrado correctamente',
            'fecha_egreso': fecha_actual.strftime("%Y-%m-%d %H:%M")
        }
    
    def obtener_historial(self, id_cta=None, limite=50):
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            
            query = """
                SELECT 
                    a.*,
                    t.apellido_nombre as titular_nombre,
                    r.fecha_ingreso, r.hora_ingreso,
                    r.fecha_egreso, r.hora_egreso,
                    r.portero_ingreso, r.portero_egreso,
                    CASE 
                        WHEN r.fecha_ingreso IS NOT NULL AND r.fecha_egreso IS NULL THEN 'Dentro'
                        WHEN r.fecha_ingreso IS NOT NULL AND r.fecha_egreso IS NOT NULL THEN 'Finalizado'
                        ELSE 'Pendiente'
                    END as estado_acceso
                FROM autorizaciones_acceso a
                LEFT JOIN titulares t ON a.id_titular = t.id
                LEFT JOIN registros_acceso r ON a.id = r.id_autorizacion
            """
            
            params = []
            if id_cta:
                query += " WHERE a.id_cta = ?"
                params.append(id_cta)
            
            query += " ORDER BY a.fecha_creacion DESC LIMIT ?"
            params.append(limite)
            
            rows = conn.execute(query, params).fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Error al obtener historial: {e}")
            return []
    
    def revocar_autorizacion(self, id_autorizacion, motivo, usuario):
        conn = get_connection()
        conn.execute("""
            UPDATE autorizaciones_acceso
            SET estado = 'Revocada',
                fecha_revocacion = ?,
                motivo_revocacion = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            motivo,
            id_autorizacion
        ))
        conn.commit()
        conn.close()
        
        self.auditoria.registrar(
            usuario=usuario,
            modulo="autorizaciones",
            accion="revocar_autorizacion",
            descripcion=f"Revocada autorización ID {id_autorizacion}"
        )
        
        return {'success': True, 'mensaje': '✅ Autorización revocada'}