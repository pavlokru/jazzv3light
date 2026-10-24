import sqlite3
import json
import os
from typing import Dict, List, Optional

class CatalogEngine:
    """Motor de persistencia SQLite optimizado con FTS5 para búsquedas ultrarrápidas."""

    def __init__(self, db_path: str = "data/catalogo.db", datos_iniciales: Optional[List[Dict]] = None):
        self.db_path = db_path
        self._preparar_entorno()
        self._inicializar_db()
        if datos_iniciales:
            self._sincronizar_datos_iniciales(datos_iniciales)

    def _preparar_entorno(self):
        directorio = os.path.dirname(self.db_path)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio, exist_ok=True)

    def _conectar(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _inicializar_db(self):
        with self._conectar() as conn:
            # Tabla principal de datos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS artistas (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT NOT NULL,
                    origen TEXT,
                    corriente TEXT,
                    instrumento TEXT,
                    tipo_agrupacion TEXT,
                    agrupaciones_propias TEXT,
                    colaboraciones_clave TEXT,
                    albumes_fundamentales TEXT,
                    anio_inicio INTEGER,
                    anio_fin INTEGER,
                    nota TEXT
                )
            """)
            
            # Tabla FTS5 Virtual para búsquedas súper rápidas de texto completo
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS artistas_fts USING fts5(
                    nombre, origen, corriente, instrumento, nota, content='artistas', content_rowid='id'
                )
            """)

            # Triggers automáticos para mantener la tabla FTS5 sincronizada con la tabla principal
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS artistas_ai AFTER INSERT ON artistas BEGIN
                    INSERT INTO artistas_fts(rowid, nombre, origen, corriente, instrumento, nota) 
                    VALUES (new.id, new.nombre, new.origen, new.corriente, new.instrumento, new.nota);
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS artistas_ad AFTER DELETE ON artistas BEGIN
                    INSERT INTO artistas_fts(artistas_fts, rowid, nombre, origen, corriente, instrumento, nota) 
                    VALUES ('delete', old.id, old.nombre, old.origen, old.corriente, old.instrumento, old.nota);
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS artistas_au AFTER UPDATE ON artistas BEGIN
                    INSERT INTO artistas_fts(artistas_fts, rowid, nombre, origen, corriente, instrumento, nota) 
                    VALUES ('delete', old.id, old.nombre, old.origen, old.corriente, old.instrumento, old.nota);
                    INSERT INTO artistas_fts(rowid, nombre, origen, corriente, instrumento, nota) 
                    VALUES (new.id, new.nombre, new.origen, new.corriente, new.instrumento, new.nota);
                END;
            """)

   
   
   
   
    def _sincronizar_datos_iniciales(self, datos: List[Dict]):
        with self._conectar() as conn:
            for item in datos:
                cursor = conn.execute("SELECT id FROM artistas WHERE id = ?", (item["id"],))
                if not cursor.fetchone():
                    self._insertar_registro(conn, item)

    def _insertar_registro(self, conn, item: Dict):
        conn.execute("""
            INSERT INTO artistas (
                id, nombre, origen, corriente, instrumento, tipo_agrupacion,
                agrupaciones_propias, colaboraciones_clave, albumes_fundamentales,
                anio_inicio, anio_fin, nota
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("id"),
            item.get("nombre"),
            item.get("origen"),
            json.dumps(item.get("corriente", [])),
            json.dumps(item.get("instrumento", [])),
            item.get("tipo_agrupacion"),
            json.dumps(item.get("agrupaciones_propias", [])),
            json.dumps(item.get("colaboraciones_clave", [])),
            json.dumps(item.get("albumes_fundamentales", [])),
            item.get("anio_inicio"),
            item.get("anio_fin"),
            item.get("nota")
        ))

    def _fila_a_dict(self, fila) -> Dict:
        d = dict(fila)
        campos_lista = ["corriente", "instrumento", "agrupaciones_propias", "colaboraciones_clave", "albumes_fundamentales"]
        for campo in campos_lista:
            # Manejar el caso donde el JSON pueda estar mal formado o ser nulo
            try:
                d[campo] = json.loads(d[campo]) if d.get(campo) else []
            except (json.JSONDecodeError, TypeError):
                d[campo] = []
        return d

    def buscar(self, criterio: str) -> List[Dict]:
        """
        Realiza una búsqueda de texto completo usando FTS5 o LIKE como respaldo.
        No usa ML ni embeddings.
        """
        criterio_norm = criterio.strip()
        if not criterio_norm:
            return self.obtener_todos()

        # Preparar término para FTS5 (agregar comodines)
        fts_query = f"*{criterio_norm}*"

        resultados = []
        with self._conectar() as conn:
            # Primero intentamos con FTS5 (muy rápido)
            try:
                 filas = conn.execute("""
                    SELECT a.* FROM artistas a
                    JOIN artistas_fts f ON a.id = f.rowid
                    WHERE artistas_fts MATCH ?
                    ORDER BY rank
                 """, (fts_query,)).fetchall()
                 
                 if filas:
                    return [self._fila_a_dict(f) for f in filas]
            except sqlite3.OperationalError:
                # Si FTS falla por sintaxis del usuario, hacemos un fallback a LIKE normal
                pass
            
            # Búsqueda LIKE (Coincidencia parcial clásica)
            like_query = f"%{criterio_norm}%"
            filas = conn.execute("""
                SELECT * FROM artistas 
                WHERE nombre LIKE ? OR origen LIKE ? OR corriente LIKE ? OR instrumento LIKE ? OR nota LIKE ?
            """, (like_query, like_query, like_query, like_query, like_query)).fetchall()
            
            return [self._fila_a_dict(f) for f in filas]


    def obtener_todos(self) -> List[Dict]:
        with self._conectar() as conn:
            filas = conn.execute("SELECT * FROM artistas ORDER BY nombre ASC").fetchall()
            return [self._fila_a_dict(f) for f in filas]

    def agregar_nota(self, item_id: int, nueva_nota: str) -> bool:
        with self._conectar() as conn:
            fila = conn.execute("SELECT nota FROM artistas WHERE id = ?", (item_id,)).fetchone()
            if not fila:
                return False
            
            nota_actual = fila["nota"]
            nota_final = f"{nota_actual}\n\n• {nueva_nota}" if nota_actual else f"• {nueva_nota}"
            
            # Al actualizar, el trigger de SQLite actualizará automáticamente el índice FTS5
            conn.execute("UPDATE artistas SET nota = ? WHERE id = ?", (nota_final, item_id))
            return True

    def agregar_item(self, nombre: str, origen: str, corriente: List[str], instrumento: List[str], tipo_agrupacion: str, agrupaciones_propias: List[str], colaboraciones_clave: List[str], albumes_fundamentales: List[str], anio_inicio: Optional[int], anio_fin: Optional[int], nota_biografica: Optional[str] = None) -> Dict:
        with self._conectar() as conn:
            cursor = conn.execute("SELECT MAX(id) FROM artistas")
            resultado_max_id = cursor.fetchone()[0]
            nuevo_id = (resultado_max_id or 0) + 1

            nuevo_item = {
                "id": nuevo_id,
                "nombre": nombre,
                "origen": origen,
                "corriente": corriente,
                "instrumento": instrumento,
                "tipo_agrupacion": tipo_agrupacion,
                "agrupaciones_propias": agrupaciones_propias,
                "colaboraciones_clave": colaboraciones_clave,
                "albumes_fundamentales": albumes_fundamentales,
                "anio_inicio": anio_inicio,
                "anio_fin": anio_fin,
                "nota": nota_biografica
            }
            self._insertar_registro(conn, nuevo_item)
            
        return nuevo_item
    
    def eliminar_artista(self, artist_id: int) -> bool:
        """
        Elimina un artista de la base de datos SQLite.
        El trigger 'artistas_ad' actualizará automáticamente la tabla FTS5.
        """
        try:
            with self._conectar() as conn:
                # Intento preventivo por si existe la tabla externa 'notas' (compatibilidad con esquemas V2)
                try:
                    conn.execute("DELETE FROM notas WHERE artista_id = ?", (artist_id,))
                except sqlite3.OperationalError:
                    pass  # En la V3.0 las notas residen en la columna 'nota' de la tabla 'artistas'

                # Eliminación principal del registro del artista
                cursor = conn.execute("DELETE FROM artistas WHERE id = ?", (artist_id,))
                
                # Si no se afectó ninguna fila, el ID no existía
                if cursor.rowcount == 0:
                    return False
                    
            return True
        except Exception as e:
            print(f"Error al eliminar artista ID {artist_id}: {e}")
            return False