"""
app.py — Punto de entrada para la aplicación web Streamlit.
"""

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import sys
import importlib.util
import os
# pyrefly: ignore [missing-import]
import graphviz
import time
import uuid
from arena_backend import get_arena_manager, PROBLEMS, PARSER_POINTS

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
# Utilidad de Visualización (Grafos)
# ─────────────────────────────────────────────────────────────────────────────

def generar_grafo_automata(parser):
    dot = graphviz.Digraph(engine="dot")
    # rankdir="LR" hace que el grafo fluya de izquierda a derecha
    dot.attr(rankdir="LR", size="10,8")
    
    for i, state in enumerate(parser.states):
        items_str = "\n".join(str(item) for item in state)
        label = f"Estado {i}\n{items_str}"
        dot.node(str(i), label, shape="box", style="rounded,filled", fillcolor="#f0f2f6")
        
    for origin, trans in parser.transitions.items():
        for symbol, dest in trans.items():
            dot.edge(str(origin), str(dest), label=symbol)
            
    return dot

# ─────────────────────────────────────────────────────────────────────────────
# Interfaz Gráfica (Streamlit)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="The Ultimate Parser App", page_icon="🚀", layout="wide")

st.title("The Ultimate Parser App 🚀")
st.subheader("Visualizador interactivo de parsers sintácticos LL(1), Descenso Recursivo, SLR(1), LR(1) y LALR(1)")

# Definición de pestañas principales
tab_parser, tab_rubrica, tab_rendimiento, tab_arena = st.tabs(["🚀 Analizador Sintáctico", "📋 Requerimientos y Rúbrica", "📊 Comparativa de Rendimiento", "⚔️ Arena 1v1"])

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

with tab_arena:
    st.header("⚔️ Arena Competitiva 1v1")
    
    if "player_name" not in st.session_state:
        st.markdown("### Bienvenido a la Arena de Parsers")
        nombre_input = st.text_input("Ingresa tu alias o nombre para competir:")
        if st.button("Entrar a la Arena", type="primary"):
            if nombre_input.strip():
                st.session_state["player_name"] = nombre_input.strip()
                st.rerun()
            else:
                st.error("Por favor, ingresa un nombre válido.")
    else:
        player_name = st.session_state["player_name"]
        
        # 1. Identificación Única de Sesión
        if "player_id" not in st.session_state:
            st.session_state["player_id"] = str(uuid.uuid4())[:8]
        player_id = st.session_state["player_id"]
        
        manager = get_arena_manager()
        
        current_game_id = None
        for gid, g in manager.games.items():
            if player_id in [g["p1"], g["p2"]] and g["status"] in ["PLAYING", "FINISHED"]:
                current_game_id = gid
                break
                
        if "searching_match" not in st.session_state:
            st.session_state["searching_match"] = False

        # 2. Flujo de Pantallas Internas
        if not current_game_id:
            # Estado de Espera (Lobby)
            if not st.session_state["searching_match"]:
                st.write(f"¡Bienvenido **{player_name}**! Enfréntate a otro jugador en tiempo real resolviendo desafíos de gramáticas.")
                if st.button("Buscar Partida 1v1", type="primary", use_container_width=True):
                    st.session_state["searching_match"] = True
                    st.rerun()
            else:
                game_id = manager.matchmaking(player_id, player_name)
                if game_id is None:
                    with st.spinner("Buscando un oponente en línea... Por favor espera."):
                        time.sleep(2)
                        st.rerun()
                else:
                    st.session_state["searching_match"] = False
                    st.rerun()
        else:
            # Estado de Juego Activo (PLAYING) o Fin (FINISHED)
            game = manager.get_game_state(current_game_id)
            if not game:
                st.error("Error al cargar la partida.")
            elif game["status"] == "PLAYING":
                opponent_id = game["p1"] if game["p2"] == player_id else game["p2"]
                my_name = game["p1_name"] if game["p1"] == player_id else game["p2_name"]
                op_name = game["p1_name"] if game["p1"] == opponent_id else game["p2_name"]
                
                my_score = game["scores"][player_id]
                op_score = game["scores"][opponent_id]
                my_q = game["current_question"][player_id]
                
                time_elapsed = int(time.time() - game["start_time"])
                time_left = max(0, 300 - time_elapsed)
                mins, secs = divmod(time_left, 60)
                
                # Cabecera
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.metric(f"Tú ({my_name})", my_score)
                with col2:
                    st.markdown(f"<h2 style='text-align: center; color: #ff4b4b;'>⚔️ {my_name}: {my_score} pts  VS  {op_name}: {op_score} pts</h2><h3 style='text-align: center; color: #ff4b4b;'>⏱️ {mins:02d}:{secs:02d}</h3>", unsafe_allow_html=True)
                    if st.button("🔄 Refrescar", use_container_width=True):
                        st.rerun()
                with col3:
                    st.metric(f"Rival ({op_name})", op_score)
                    
                st.divider()
                
                # Cuerpo
                if my_q < len(PROBLEMS):
                    problem = PROBLEMS[my_q]
                    st.info(f"**Desafío {my_q + 1} / {len(PROBLEMS)}**: {problem['descripcion']}")
                    
                    def format_parser_option(p):
                        puntos = PARSER_POINTS.get(p, 2)
                        return f"{p} (+{puntos} pts)"
                    
                    parser_elegido = st.radio(
                        "Elige tu Parser (Mayor dificultad = Más puntos)", 
                        options=["LL(1)", "SLR(1)", "LALR(1)", "LR(1)"],
                        format_func=format_parser_option,
                        horizontal=True,
                        key=f"radio_{my_q}"
                    )
                    
                    grammar_ans = st.text_area("Escribe tu gramática aquí:", height=150, key=f"ans_{my_q}")
                    
                    # Acción del Botón
                    if st.button("Enviar Solución 🚀", use_container_width=True):
                        success = manager.submit_answer(current_game_id, player_id, grammar_ans, parser_elegido)
                        if success:
                            puntos_ganados = PARSER_POINTS.get(parser_elegido, 2)
                            st.success(f"¡Respuesta correcta! Usaste {parser_elegido} y sumaste {puntos_ganados} puntos. 🎉")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            st.error("❌ La gramática no es correcta (falla en las pruebas o sintaxis). Intenta de nuevo.")
                else:
                    st.success("¡Has completado todos los desafíos! Esperando al rival o al final del tiempo...")
                    if st.button("Comprobar Estado 🔄"):
                        st.rerun()
                        
            # Estado de Fin de Juego (FINISHED)
            elif game["status"] == "FINISHED":
                st.header("🏁 ¡Partida Finalizada!")
                opponent_id = game["p1"] if game["p2"] == player_id else game["p2"]
                my_name = game["p1_name"] if game["p1"] == player_id else game["p2_name"]
                op_name = game["p1_name"] if game["p1"] == opponent_id else game["p2_name"]
                
                my_score = game["scores"][player_id]
                op_score = game["scores"][opponent_id]
                
                st.subheader(f"Puntuación Final: {my_name} {my_score} - {op_score} {op_name}")
                
                winner = game.get("winner")
                if winner == player_id:
                    st.success("🏆 ¡Felicidades! Has ganado la arena de gramáticas.")
                    st.balloons()
                elif winner == "TIE":
                    st.info("🤝 ¡Es un empate! Bien jugado.")
                else:
                    st.error("💔 Has perdido esta vez. ¡Sigue practicando!")
                    
                if st.button("Salir al Menú Principal", type="primary"):
                    del st.session_state["player_id"]
                    if "searching_match" in st.session_state:
                        del st.session_state["searching_match"]
                    st.rerun()

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
            
            with st.expander("Ver Autómata de Estados (Grafo)"):
                st.graphviz_chart(generar_grafo_automata(parser))
            
            # Análisis Shift-Reduce Paso a Paso
            st.markdown("#### Paso a Paso (Shift-Reduce)")
            log = parser.parse(tokens)
            st.table(pd.DataFrame(log))

        # Éxito
        st.success("¡Análisis sintáctico completado exitosamente! 🎉")

        with tab_rendimiento:
            st.markdown("### 📊 Comparativa de Rendimiento")
            st.info("Ejecutando la gramática y cadena en todos los motores de parsing...")
            
            def compare_parsers(grammar: Grammar, input_tokens: list[str]):
                results = []
                parsers_to_test = [
                    ("LL(1)", LL1Parser, False),
                    ("SLR(1)", SLR1Parser, True),
                    ("LR(1)", LR1Parser, True),
                    ("LALR(1)", LALR1Parser, True)
                ]
                
                for name, ParserClass, is_bottom_up in parsers_to_test:
                    accepted = "No"
                    steps = "-"
                    states_count = "N/A"
                    try:
                        p = ParserClass(grammar)
                        if is_bottom_up:
                            states_count = len(p.states)
                        log = p.parse(input_tokens)
                        accepted = "Sí"
                        steps = len(log)
                    except SyntaxError:
                        accepted = "Error: Sintaxis"
                        if is_bottom_up and 'p' in locals():
                            states_count = len(p.states)
                    except ValueError:
                        accepted = "Error: Conflicto"
                    except Exception as e:
                        accepted = "Error"
                        
                    results.append({
                        "Algoritmo": name,
                        "¿Aceptada?": accepted,
                        "Pasos de Pila": steps,
                        "Cantidad de Estados": states_count
                    })
                    
                return results

            metrics = compare_parsers(g, tokens)
            df_metrics = pd.DataFrame(metrics)
            
            st.markdown("#### Tabla de Resultados")
            st.table(df_metrics.set_index("Algoritmo"))
            
            bottom_up_metrics = [m for m in metrics if isinstance(m["Cantidad de Estados"], int)]
            if bottom_up_metrics:
                st.markdown("#### Cantidad de Estados (Bottom-Up)")
                df_chart = pd.DataFrame(bottom_up_metrics).set_index("Algoritmo")
                st.bar_chart(df_chart["Cantidad de Estados"])

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
