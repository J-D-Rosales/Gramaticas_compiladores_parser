import time
import uuid
import sys
import os
import importlib.util
# pyrefly: ignore [missing-import]
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Importación Robusta de Módulos (Grammar y Parsers)
# ─────────────────────────────────────────────────────────────────────────────

def load_parser_module(module_name: str, file_names: list[str]):
    for file_name in file_names:
        if os.path.exists(file_name):
            spec = importlib.util.spec_from_file_location(module_name, file_name)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                return module
    raise ImportError(f"No se pudo encontrar el módulo {module_name}")

try:
    grammar_module = load_parser_module("grammar", ["grammar.py"])
    Grammar = grammar_module.Grammar
except ImportError:
    pass

try:
    top_down = load_parser_module("top_down", ["top_down.py", "top-down.py"])
    LL1Parser = top_down.LL1Parser
except ImportError:
    pass

try:
    bottom_up = load_parser_module("bottom_up", ["bottom_up.py", "bottom-up.py"])
    SLR1Parser = bottom_up.SLR1Parser
    LR1Parser = bottom_up.LR1Parser
    LALR1Parser = bottom_up.LALR1Parser
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────────────────────
# Banco de Desafíos (10 Problemas)
# ─────────────────────────────────────────────────────────────────────────────

PROBLEMS = [
    {
        "id": 1,
        "descripcion": "Diseña una gramática que reconozca el lenguaje a^n b^n (misma cantidad de a y b). Símbolo inicial: S.",
        "validas": ["a b $", "a a b b $", "a a a b b b $"],
        "invalidas": ["a a b $", "a b b $", "b a $", "a $", "b $"]
    },
    {
        "id": 2,
        "descripcion": "Diseña una gramática para secuencias de paréntesis balanceados simples. Símbolo inicial: S.",
        "validas": ["( ) $", "( ( ) ) $", "( ) ( ) $", "( ( ( ) ) ) $"],
        "invalidas": ["( ( ) $", "( ) ) $", ") ( $", "( $", ") $"]
    },
    {
        "id": 3,
        "descripcion": "Diseña una gramática para listas de uno o más identificadores ('id') separados por comas. Símbolo inicial: L.",
        "validas": ["id $", "id , id $", "id , id , id $"],
        "invalidas": ["id , $", ", id $", "id id $", ", $"]
    },
    {
        "id": 4,
        "descripcion": "Diseña una gramática que reconozca cadenas con alternancia estricta de 'a' y 'b', comenzando siempre con 'a'. Símbolo inicial: S.",
        "validas": ["a $", "a b $", "a b a $", "a b a b $"],
        "invalidas": ["b $", "a a $", "a b b $", "b a b $"]
    },
    {
        "id": 5,
        "descripcion": "Diseña una gramática para palíndromos sobre {a, b} separados por un centro 'c' (w c w^R). Símbolo inicial: S.",
        "validas": ["c $", "a c a $", "b c b $", "a b c b a $", "b a c a b $"],
        "invalidas": ["a c b $", "a b c a b $", "c c $", "a c $"]
    },
    {
        "id": 6,
        "descripcion": "Diseña una gramática que reconozca el lenguaje a^n b^2n (una 'a' seguida del doble de 'b's). Símbolo inicial: S.",
        "validas": ["a b b $", "a a b b b b $", "a a a b b b b b b $"],
        "invalidas": ["a b $", "a b b b $", "a a b b b $"]
    },
    {
        "id": 7,
        "descripcion": "Diseña una gramática para expresiones de sumas simples usando 'id' y el operador '+'. Símbolo inicial: E.",
        "validas": ["id $", "id + id $", "id + id + id $"],
        "invalidas": ["id + $", "+ id $", "id id $", "+ $"]
    },
    {
        "id": 8,
        "descripcion": "Diseña una gramática para bloques if-then y if-then-else terminados explícitamente con 'end'. Símbolo inicial: S.",
        "validas": ["if id then id end $", "if id then if id then id end else id end $"],
        "invalidas": ["if id then id $", "if id then id else id $", "if then end $"]
    },
    {
        "id": 9,
        "descripcion": "Diseña una gramática para la asignación básica a variables: 'id = num'. Símbolo inicial: A.",
        "validas": ["id = num $"],
        "invalidas": ["= num $", "id = $", "id id $", "num = id $"]
    },
    {
        "id": 10,
        "descripcion": "Diseña una gramática para el acceso a arrays usando corchetes: 'id [ num ]'. Símbolo inicial: A.",
        "validas": ["id [ num ] $"],
        "invalidas": ["id [ ] $", "id num ] $", "id [ num $", "[ num ] $"]
    }
]

# ─────────────────────────────────────────────────────────────────────────────
# Juez Automático
# ─────────────────────────────────────────────────────────────────────────────

def evaluar_solucion(gramatica_texto: str, lista_validas: list[str], lista_invalidas: list[str], parser_elegido: str) -> bool:
    """
    Evalúa la gramática ingresada contra las cadenas válidas e inválidas del problema.
    Retorna True si supera TODAS las pruebas, False en caso contrario.
    """
    # 1. Intentar compilar la gramática
    try:
        g = Grammar(gramatica_texto)
        if parser_elegido == "LL(1)":
            parser = LL1Parser(g)
        elif parser_elegido == "SLR(1)":
            parser = SLR1Parser(g)
        elif parser_elegido == "LALR(1)":
            parser = LALR1Parser(g)
        elif parser_elegido == "LR(1)":
            parser = LR1Parser(g)
        else:
            return False
    except Exception:
        # Error de sintaxis en la gramática, no es el parser elegido, o formato inválido
        return False
        
    # 2. Evaluar cadenas válidas (DEBEN ser aceptadas)
    for valid_str in lista_validas:
        tokens = valid_str.strip().split()
        if tokens and tokens[-1] == "$":
            tokens = tokens[:-1]
            
        try:
            parser.parse(tokens)
        except Exception:
            return False # Falló en una cadena que debía aceptar
            
    # 3. Evaluar cadenas inválidas (DEBEN ser rechazadas)
    for invalid_str in lista_invalidas:
        tokens = invalid_str.strip().split()
        if tokens and tokens[-1] == "$":
            tokens = tokens[:-1]
            
        try:
            parser.parse(tokens)
            return False # La aceptó, pero debía fallar
        except Exception:
            pass # Falló como se esperaba, correcto
            
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Administrador Global de la Arena
# ─────────────────────────────────────────────────────────────────────────────

PARSER_POINTS = {
    "LL(1)": 10,
    "SLR(1)": 5,
    "LALR(1)": 4,
    "LR(1)": 2
}

class ArenaManager:
    """
    Controla el estado centralizado de los jugadores y las partidas.
    """
    def __init__(self):
        self.games = {}
        self.waiting_player = None
        
    def matchmaking(self, player_id: str, player_name: str):
        """
        Empareja jugadores. Si hay uno esperando, crea la partida. 
        Si no, pone al jugador en cola.
        Retorna el game_id si está en una partida, o None si sigue en cola.
        """
        # Verificar si el jugador ya está en una partida activa
        for game_id, game in self.games.items():
            if player_id in [game["p1"], game["p2"]] and game["status"] == "PLAYING":
                if time.time() - game["start_time"] > 300: # 5 minutos
                    game["status"] = "FINISHED"
                return game_id

        # Si soy yo mismo quien está esperando, sigo en cola
        if self.waiting_player and self.waiting_player["id"] == player_id:
            self.waiting_player["name"] = player_name
            return None

        # Si hay un oponente esperando, crear la partida
        if self.waiting_player is not None:
            opponent_id = self.waiting_player["id"]
            opponent_name = self.waiting_player["name"]
            game_id = str(uuid.uuid4())
            self.games[game_id] = {
                "p1": opponent_id,
                "p2": player_id,
                "p1_name": opponent_name,
                "p2_name": player_name,
                "scores": {opponent_id: 0, player_id: 0},
                "current_question": {opponent_id: 0, player_id: 0},
                "start_time": time.time(),
                "status": "PLAYING",
                "winner": None
            }
            self.waiting_player = None
            return game_id
            
        # Si no hay nadie, me pongo en cola
        else:
            self.waiting_player = {"id": player_id, "name": player_name}
            return None

    def submit_answer(self, game_id: str, player_id: str, grammar_text: str, parser_elegido: str = "LR(1)") -> bool:
        """
        Verifica la respuesta del jugador. Actualiza su puntuación si es correcta.
        Retorna True si acertó, False si falló.
        """
        if game_id not in self.games:
            return False
            
        game = self.games[game_id]
        
        if game["status"] != "PLAYING":
            return False
            
        if time.time() - game["start_time"] > 300:
            game["status"] = "FINISHED"
            return False

        q_idx = game["current_question"][player_id]
        if q_idx >= len(PROBLEMS):
            return False
            
        problem = PROBLEMS[q_idx]
        success = evaluar_solucion(grammar_text, problem["validas"], problem["invalidas"], parser_elegido)
        
        if success:
            puntos = PARSER_POINTS.get(parser_elegido, 2)
            game["scores"][player_id] += puntos
            game["current_question"][player_id] += 1
            
            # Si completó todas las preguntas, gana y finaliza la partida
            if game["current_question"][player_id] >= len(PROBLEMS):
                game["status"] = "FINISHED"
                game["winner"] = player_id
            return True
            
        return False
        
    def get_game_state(self, game_id: str):
        """
        Retorna el estado actual de la partida, controlando la expiración de tiempo.
        """
        if game_id in self.games:
            game = self.games[game_id]
            if game["status"] == "PLAYING" and time.time() - game["start_time"] > 300:
                game["status"] = "FINISHED"
                
                # Determinar ganador por puntos si acabó el tiempo
                s1 = game["scores"][game["p1"]]
                s2 = game["scores"][game["p2"]]
                if s1 > s2:
                    game["winner"] = game["p1"]
                elif s2 > s1:
                    game["winner"] = game["p2"]
                else:
                    game["winner"] = "TIE"
                    
            return game
        return None

# ─────────────────────────────────────────────────────────────────────────────
# Cache de Streamlit para instancia compartida
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_arena_manager() -> ArenaManager:
    """
    Patrón Singleton en Streamlit para compartir memoria entre sesiones.
    """
    return ArenaManager()
