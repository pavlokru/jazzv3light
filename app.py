import streamlit as st
import os
import json
from src.db import CatalogEngine

# Configuración de página
st.set_page_config(
    page_title="JazzCatalog V3 (Light)",
    page_icon="🎷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para Badges y Tarjetas
st.markdown("""
<style>
    .badge-corriente {
        display: inline-block; padding: 3px 8px; font-size: 12px; font-weight: 600;
        border-radius: 12px; background-color: #2b5c8f; color: #ffffff;
        margin-right: 4px; margin-bottom: 4px;
    }
    .badge-inst {
        display: inline-block; padding: 3px 8px; font-size: 12px; font-weight: 600;
        border-radius: 12px; background-color: #4a5568; color: #ffffff;
        margin-right: 4px; margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Conectando a SQLite...")
def obtener_motor():
    datos_iniciales = None
    if os.path.exists("data/data.py"):
        try:
            from data.data import dataset # type: ignore
            datos_iniciales = dataset
        except Exception:
            pass
            
    engine = CatalogEngine(datos_iniciales=datos_iniciales)
    return engine


engine = obtener_motor()

# ==========================================
# BARRA LATERAL (Métricas y Filtros)
# ==========================================
with st.sidebar:
    st.header("🎷JazzCatalog")
    st.caption("Sistema de Búsqueda Rápida v3.0 (SQLite FTS)")
    st.divider()
    
    todos_artistas = engine.obtener_todos()
    total_artistas = len(todos_artistas)
    
    corrientes_unicas = set()
    instrumentos_unicos = set()
    for a in todos_artistas:
        corrientes_unicas.update(a.get("corriente", []))
        instrumentos_unicos.update(a.get("instrumento", []))
        
    st.metric(label="Total Artistas", value=total_artistas)
    col_m1, col_m2 = st.columns(2)
    col_m1.metric(label="Estilos", value=len(corrientes_unicas))
    col_m2.metric(label="Instrumentos", value=len(instrumentos_unicos))


# ==========================================
# ESTRUCTURA PRINCIPAL DE NAVEGACIÓN
# ==========================================
st.title("🎷JazzCatalog V3")
st.markdown("Directorio ligero y ultrarrápido con búsqueda de texto completo.")

tab_busqueda, tab_explorador, tab_gestion = st.tabs([
    "🔍 Búsqueda Rápida", 
    "📚 Directorio Completo", 
    "📝 Gestión del Catálogo"
])


# ------------------------------------------
# TAB 1: BÚSQUEDA RÁPIDA (FTS5)
# ------------------------------------------
with tab_busqueda:
    st.markdown("**Búsqueda instantánea en todos los campos (nombre, origen, estilo, biografía, etc.)**")
    query = st.text_input("Ingresa términos de búsqueda", placeholder="Ej: Pioneros Bebop Cuba", key="input_query")

    if query.strip():
        resultados = engine.buscar(query)
        if resultados:
            st.subheader(f"Resultados Encontrados ({len(resultados)})")
            for res in resultados:
                with st.expander(f"{res['nombre']} - {res.get('origen', 'Origen N/D')}"):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.write(f"**Estilos:** {', '.join(res.get('corriente', []))}")
                        st.write(f"**Instrumentos:** {', '.join(res.get('instrumento', []))}")
                    with c2:
                         if res.get("nota"):
                            st.info(f"**Extracto:** {res.get('nota')[:200]}...")
        else:
            st.warning("No se encontraron coincidencias en la base de datos.")


# ------------------------------------------
# TAB 2: EXPLORADOR COMPLETO
# ------------------------------------------
with tab_explorador:
    st.subheader("Directorio General")
    
    # Filtro en memoria (Python) para exploración rápida de todo el listado
    filtro_texto = st.text_input(
        "🔍 Filtrar listado actual", 
        placeholder="Ej: Trompeta...",
        key="filtro_tab2"
    )
    
    artistas_filtrados = todos_artistas
    if filtro_texto.strip():
        f = filtro_texto.lower()
        artistas_filtrados = [
            a for a in todos_artistas 
            if f in str(a.get('nombre', '')).lower() 
            or f in str(a.get('origen', '')).lower()
            or any(f in str(c).lower() for c in a.get('corriente', []))
            or any(f in str(i).lower() for i in a.get('instrumento', []))
        ]
        
    st.caption(f"Mostrando {len(artistas_filtrados)} registros.")
    
    for art in artistas_filtrados:
        with st.expander(f"👤 {art['nombre']} ({art.get('origen', 'Origen N/D')})"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Tipo de Agrupación:** {art.get('tipo_agrupacion', 'N/D')}")
                st.write(f"**Corrientes:** {', '.join(art.get('corriente', []))}")
                st.write(f"**Instrumentos:** {', '.join(art.get('instrumento', []))}")
                st.write(f"**Agrupaciones Propias:** {', '.join(art.get('agrupaciones_propias', []))}")
            with c2:
                st.write(f"**Colaboraciones Clave:** {', '.join(art.get('colaboraciones_clave', []))}")
                st.write(f"**Álbumes Fundamentales:** {', '.join(art.get('albumes_fundamentales', []))}")
                st.write(f"**Período de Actividad:** {art.get('anio_inicio', 'N/D')} - {art.get('anio_fin') or 'Presente'}")
            
            if art.get("nota"):
                st.info(f"**Biografía / Notas:**\n\n{art.get('nota')}")


# ------------------------------------------
# TAB 3: GESTIÓN DE CATÁLOGO
# ------------------------------------------

# ------------------------------------------
# TAB 3: GESTIÓN DE CATÁLOGO (Sección Eliminar)
# ------------------------------------------
with tab_gestion:
    # ... (Formularios existentes de inserción y notas) ...

    st.divider()

    # Sección: Eliminar Artista
    st.subheader("🗑️ Eliminar Artista del Catálogo")
    st.warning("⚠️ Esta acción es permanente y eliminará al artista junto con todos sus datos asociados.")

    opciones_borrar = {f"{a['nombre']} (ID: {a['id']})": a['id'] for a in todos_artistas}

    if opciones_borrar:
        with st.form("form_eliminar_artista", clear_on_submit=True):
            seleccionado_borrar = st.selectbox(
                "Seleccionar artista a eliminar", 
                options=list(opciones_borrar.keys())
            )
            btn_eliminar = st.form_submit_button("❌ Confirmar y Eliminar Artista")
            
            if btn_eliminar:
                id_a_eliminar = opciones_borrar[seleccionado_borrar]
                if engine.eliminar_artista(id_a_eliminar):
                    st.toast("Artista eliminado correctamente.", icon="🗑️")
                    st.rerun()
                else:
                    st.error("No se pudo eliminar el registro.")
    else:
        st.info("No hay artistas disponibles para eliminar.")



with tab_gestion:
    col_add, col_note = st.columns([1.2, 0.8])
    
    # Formulario: Agregar nuevo artista
    with col_add:
        st.subheader("Añadir Registro (Perfil Completo)")
        with st.form("form_nuevo_artista_v3", clear_on_submit=True):
            nombre = st.text_input("Nombre completo del artista / banda*")
            origen = st.text_input("Origen (País, Ciudad)")
            
            c_t1, c_t2 = st.columns(2)
            tipo_agrupacion = c_t1.text_input("Tipo de agrupación (Ej: Solista, Quinteto)")
            agrupaciones_raw = c_t2.text_input("Agrupaciones propias (separadas por comas)")
            
            corriente_raw = st.text_input("Corrientes (separadas por comas)")
            instrumento_raw = st.text_input("Instrumentos (separados por comas)")
            colabs_raw = st.text_input("Colaboraciones clave (separadas por comas)")
            albumes_raw = st.text_area("Álbumes fundamentales (separados por comas)")
            
            c_a1, c_a2 = st.columns(2)
            anio_inicio = c_a1.number_input("Año inicio", min_value=1800, max_value=2100, value=1970)
            anio_fin = c_a2.number_input("Año fin (0 si sigue activo)", min_value=0, max_value=2100, value=0)
            
            nota_biografica = st.text_area("Nota biográfica / Apunte histórico (Opcional)", height=150)
            
            btn_guardar = st.form_submit_button("Guardar Perfil")
            
            if btn_guardar:
                if not nombre.strip():
                    st.error("El nombre es obligatorio.")
                else:
                    lista_corriente = [x.strip() for x in corriente_raw.split(",") if x.strip()]
                    lista_instrumento = [x.strip() for x in instrumento_raw.split(",") if x.strip()]
                    lista_agrup = [x.strip() for x in agrupaciones_raw.split(",") if x.strip()]
                    lista_colabs = [x.strip() for x in colabs_raw.split(",") if x.strip()]
                    lista_albumes = [x.strip() for x in albumes_raw.split(",") if x.strip()]
                    
                    a_fin = None if anio_fin == 0 else int(anio_fin)
                    
                    engine.agregar_item(
                        nombre=nombre.strip(),
                        origen=origen.strip(),
                        corriente=lista_corriente,
                        instrumento=lista_instrumento,
                        tipo_agrupacion=tipo_agrupacion.strip(),
                        agrupaciones_propias=lista_agrup,
                        colaboraciones_clave=lista_colabs,
                        albumes_fundamentales=lista_albumes,
                        anio_inicio=int(anio_inicio),
                        anio_fin=a_fin,
                        nota_biografica=nota_biografica.strip() if nota_biografica.strip() else None
                    )
                    
                    st.toast(f"¡{nombre} registrado exitosamente!", icon="✅")
                    st.rerun()

    # Formulario: Agregar notas adicionales a artista existente
    with col_note:
        st.subheader("Añadir Apuntes Adicionales")
        
        opciones_artistas = {f"{a['nombre']} (ID: {a['id']})": a['id'] for a in todos_artistas}
        
        if opciones_artistas:
            with st.form("form_agregar_nota_v3", clear_on_submit=True):
                seleccionado = st.selectbox("Seleccionar artista", options=list(opciones_artistas.keys()))
                nueva_nota = st.text_area("Nuevo apunte o actualización")
                
                btn_nota = st.form_submit_button("Guardar Nota")
                
                if btn_nota and nueva_nota.strip():
                    artist_id = opciones_artistas[seleccionado]
                    if engine.agregar_nota(artist_id, nueva_nota.strip()):
                        st.toast("Nota agregada correctamente", icon="📌")
                        st.rerun()
                    else:
                        st.error("Error al guardar la nota.")
        else:
            st.info("El catálogo está vacío.")

    st.divider()
    
    # Sección de Respaldos
    st.subheader("💾 Respaldo de Base de Datos")
    st.info("Descarga la base de datos SQLite con todos tus registros.")
    
    db_path = "data/catalogo.db"
    
    if os.path.exists(db_path):
        with open(db_path, "rb") as f:
            st.download_button(
                label="⬇️ Descargar catalogo.db",
                data=f,
                file_name="catalogo.db",
                mime="application/octet-stream",
                use_container_width=True
            )
    else:
        st.warning("El archivo de base de datos aún no se ha creado.")