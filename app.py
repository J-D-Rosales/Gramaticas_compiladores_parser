"""
app.py — Punto de entrada para la aplicación web Streamlit.
"""

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import sys
import importlib.util
import os

# ─────────────────────────────────────────────────────────────────────────────
# Importación Robusta (para manejar archivos con guiones o guiones bajos)
# ─────────────────────────────────────────────────────────────────────────────

def load_parser_module(module_name: str, file_names: list[str]):
    """Carga un módulo intentando múltiples nombres de archivo para evitar errores."""
    for file_name in file_names:
        if os.path.exists(file_name):
            spec = importlib.util.spec_from_file_location(module_name, file_name)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return module
    raise ImportError(f"No se pudo encontrar el módulo {module_name}")

from grammar import Grammar

# Importar Top-Down Parsers
try:
    # pyrefly: ignore [missing-import]
    from top_down import LL1Parser, RecursiveDescentParser
except ImportError:
    top_down = load_parser_module("top_down", ["top_down.py", "top-down.py"])
    LL1Parser = top_down.LL1Parser
    RecursiveDescentParser = top_down.RecursiveDescentParser

# Importar Bottom-Up Parsers
try:
    # pyrefly: ignore [missing-import]
    from bottom_up import SLR1Parser, LR1Parser, LALR1Parser
except ImportError:
    bottom_up = load_parser_module("bottom_up", ["bottom_up.py", "bottom-up.py"])
    SLR1Parser = bottom_up.SLR1Parser
    LR1Parser = bottom_up.LR1Parser
    LALR1Parser = bottom_up.LALR1Parser

# ─────────────────────────────────────────────────────────────────────────────
# Interfaz Gráfica (Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="The Ultimate Parser App", page_icon="🚀", layout="wide")

st.title("The Ultimate Parser App 🚀")
st.subheader("Visualizador interactivo de parsers sintácticos LL(1), Descenso Recursivo, SLR(1), LR(1) y LALR(1)")

# Definición de pestañas principales
tab_parser, tab_rubrica = st.tabs(["🚀 Analizador Sintáctico", "📋 Requerimientos y Rúbrica"])

with tab_parser:
    st.subheader("Resultados del Análisis")
    # ... Aquí mantienes toda tu lógica de ejecución de código existente ...

with tab_rubrica:
    st.subheader("Documentación del Proyecto")
    
    # 1. Cargar e Inyectar la Guía de Uso Rápida
    try:
        with open("rubrica.html", "r", encoding="utf-8") as f:
            html_instrucciones = f.read()
        st.markdown(html_instrucciones, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("No se encontró el archivo 'rubrica.html'. Asegúrate de crearlo en la raíz.")

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.header("Configuración")
    
    default_grammar = (
        "E -> T E'\n"
        "E' -> + T E' | epsilon\n"
        "T -> F T'\n"
        "T' -> * F T' | epsilon\n"
        "F -> ( E ) | id"
    )
    
    grammar_text = st.text_area("Gramática:", value=default_grammar, height=250)
    
    input_string = st.text_input("Cadena a evaluar:", value="id + id $")
    
    parser_choice = st.selectbox(
        "Seleccione el Parser:", 
        ["LL(1)", "Descenso Recursivo", "SLR(1)", "LR(1)", "LALR(1)"]
    )
    
    analyze_btn = st.button("Analizar", type="primary", use_container_width=True)


# --- Área Principal (Main) ---
if analyze_btn:
    try:
        # 1. Instanciar la Gramática
        g = Grammar(grammar_text)
        
        st.markdown("### 1. Conjuntos FIRST y FOLLOW")
        ff_data = []
        for nt in g._ordered_nonterminals():
            ff_data.append({
                "No Terminal": nt,
                "FIRST": "{ " + ", ".join(sorted(g.first[nt])) + " }",
                "FOLLOW": "{ " + ", ".join(sorted(g.follow[nt])) + " }"
            })
        df_ff = pd.DataFrame(ff_data).set_index("No Terminal")
        st.table(df_ff)
        
        # 2. Preparar los tokens de entrada
        tokens = input_string.strip().split()
        if not tokens:
            tokens = ["$"]
            
        st.markdown(f"### 2. Análisis con: {parser_choice}")
        
        # 3. Selección y ejecución del Parser
        if parser_choice == "LL(1)":
            parser = LL1Parser(g)
            
            # Mostrar Tabla Predictiva LL(1)
            st.markdown("#### Tabla Predictiva M[A, a]")
            table_data = {}
            for nt in g.non_terminals:
                table_data[nt] = {}
                for term in (g.terminals | {"$"}):
                    if term in parser.table.get(nt, {}):
                        table_data[nt][term] = f"{nt} -> {' '.join(parser.table[nt][term])}"
                    else:
                        table_data[nt][term] = ""
            
            cols = sorted(list(g.terminals)) + ["$"]
            df_table = pd.DataFrame.from_dict(table_data, orient='index').fillna("")
            st.dataframe(df_table[cols], use_container_width=True)
            
            # Análisis Paso a Paso
            st.markdown("#### Paso a Paso (Pila y Validación)")
            log = parser.parse(tokens)
            st.table(pd.DataFrame(log))
            
        elif parser_choice == "Descenso Recursivo":
            parser = RecursiveDescentParser(g, tokens)
            
            # Log de llamadas recursivas
            st.markdown("#### Log de Llamadas (Simulación)")
            log = parser.parse()
            formatted_log = []
            for entry in log:
                indent = "    " * entry["profundidad"]
                formatted_log.append({
                    "Procedimiento": indent + entry["procedimiento"],
                    "Acción": entry["accion"],
                    "Entrada Restante": entry["entrada_restante"]
                })
            st.table(pd.DataFrame(formatted_log))
            
        elif parser_choice in ["SLR(1)", "LR(1)", "LALR(1)"]:
            if parser_choice == "SLR(1)":
                parser = SLR1Parser(g)
            elif parser_choice == "LR(1)":
                parser = LR1Parser(g)
            elif parser_choice == "LALR(1)":
                parser = LALR1Parser(g)
            
            # Mostrar Tablas ACTION y GOTO
            st.markdown("#### Tablas ACTION y GOTO")
            terminals = sorted(list(g.terminals)) + ["$"]
            non_terminals = [nt for nt in g._ordered_nonterminals() if nt != parser.augmented_start]
            
            combined_data = []
            for i in range(len(parser.states)):
                row = {"Estado": str(i)}
                for t in terminals:
                    row[t] = parser.action_table[i].get(t, "")
                for nt in non_terminals:
                    val = parser.goto_table[i].get(nt, "")
                    row[nt] = str(val) if val != "" else ""
                combined_data.append(row)
                
            df_tables = pd.DataFrame(combined_data).set_index("Estado")
            st.dataframe(df_tables, use_container_width=True)
            
            # Análisis Shift-Reduce Paso a Paso
            st.markdown("#### Paso a Paso (Shift-Reduce)")
            log = parser.parse(tokens)
            st.table(pd.DataFrame(log))

        # Éxito
        st.success("¡Análisis sintáctico completado exitosamente! 🎉")

    except SyntaxError as se:
        st.error("🚨 Error de Sintaxis (La cadena no pertenece al lenguaje)")
        st.error(str(se))
        
        # En caso de descenso recursivo, mostrar hasta dónde llegó
        if parser_choice == "Descenso Recursivo" and 'parser' in locals():
            st.warning("Traza de llamadas generada hasta el momento del error:")
            formatted_log = []
            for entry in parser.log:
                indent = "    " * entry["profundidad"]
                formatted_log.append({
                    "Procedimiento": indent + entry["procedimiento"],
                    "Acción": entry["accion"],
                    "Entrada Restante": entry["entrada_restante"]
                })
            if formatted_log:
                st.table(pd.DataFrame(formatted_log))

    except ValueError as ve:
        st.error("🚨 Conflicto en la Gramática detectado al construir la tabla")
        st.error(str(ve))
        
    except Exception as e:
        st.error(f"🚨 Error Inesperado: {str(e)}")

else:
    st.info("👈 Configura la gramática en la barra lateral y presiona 'Analizar' para comenzar.")
