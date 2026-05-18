"""
top_down.py — Parsers descendentes (Top-Down) para gramáticas LL(1).

Contiene dos implementaciones:
  1. LL1Parser        – Parser predictivo dirigido por tabla.
  2. RecursiveDescentParser – Simulación genérica de descenso recursivo
                              guiado por la tabla LL(1) para evitar
                              problemas de recursividad izquierda.

Ambas clases dependen de la clase Grammar definida en grammar.py.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from grammar import EPSILON, END_MARKER, Grammar


# ─────────────────────────────────────────────────────────────────────────────
# Parser LL(1) — Dirigido por Tabla Predictiva
# ─────────────────────────────────────────────────────────────────────────────

class LL1Parser:
    """Parser predictivo LL(1) basado en tabla.

    Construye la tabla predictiva M[A, a] según el algoritmo 4.31 del
    Libro del Dragón y simula el autómata de pila para validar cadenas
    tokenizadas.

    Atributos públicos:
        grammar : Grammar
            Gramática subyacente (ya con FIRST y FOLLOW calculados).
        table   : dict[str, dict[str, list[str]]]
            Tabla predictiva.  table[A][a] contiene la producción (como
            lista de tokens) que debe aplicarse cuando el No Terminal A
            está en el tope de la pila y el token de entrada es a.
    """

    def __init__(self, grammar: Grammar) -> None:
        """Inicializa el parser LL(1).

        Args:
            grammar: Objeto Grammar ya construido.
        """
        self.grammar: Grammar = grammar
        self.table: Dict[str, Dict[str, List[str]]] = {}
        self.build_table()

    # ── Construcción de la tabla LL(1) ───────────────────────────────────
    def build_table(self) -> None:
        """Construye la tabla predictiva M[A, a].

        Algoritmo (Dragon Book, Algoritmo 4.31):
            Para cada producción A → α:
              1. Para cada terminal *a* en FIRST(α), agregar A → α a M[A, a].
              2. Si epsilon ∈ FIRST(α), para cada terminal *b* (incluido $)
                 en FOLLOW(A), agregar A → α a M[A, b].
              3. Las celdas sin producción representan errores sintácticos.

        Raises:
            ValueError: Si se detecta un conflicto en la tabla, lo que
                        indica que la gramática **no** es LL(1).
        """
        g: Grammar = self.grammar

        # Universo de columnas: terminales + $.
        columns: Set[str] = g.terminals | {END_MARKER}

        # Inicializar tabla vacía.
        self.table = {nt: {} for nt in g.non_terminals}

        for nt in g.non_terminals:
            for production in g.productions[nt]:
                first_alpha: Set[str] = g.first_of(production)

                # Regla 1: para cada terminal a ∈ FIRST(α).
                for a in first_alpha - {EPSILON}:
                    self._set_table_entry(nt, a, production)

                # Regla 2: si ε ∈ FIRST(α), usar FOLLOW(A).
                if EPSILON in first_alpha:
                    for b in g.follow[nt]:
                        self._set_table_entry(nt, b, production)

    def _set_table_entry(
        self, nt: str, terminal: str, production: List[str]
    ) -> None:
        """Asigna una producción a la celda M[nt, terminal].

        Raises:
            ValueError: Si la celda ya contiene una producción diferente
                        (conflicto LL(1)).
        """
        if terminal in self.table[nt]:
            existing: List[str] = self.table[nt][terminal]
            if existing != production:
                raise ValueError(
                    f"Conflicto LL(1) en M[{nt}, {terminal}]: "
                    f"ya tiene {nt} -> {' '.join(existing)}, "
                    f"se intentó agregar {nt} -> {' '.join(production)}. "
                    f"La gramática NO es LL(1)."
                )
        else:
            self.table[nt][terminal] = production

    # ── Simulación del parser de pila ────────────────────────────────────
    def parse(self, tokens: List[str]) -> List[Dict[str, str]]:
        """Simula el autómata de pila del parser predictivo LL(1).

        Args:
            tokens: Lista de tokens de entrada.  Debe terminar con '$'.
                    Ejemplo: ``["id", "+", "id", "$"]``.

        Returns:
            Lista de diccionarios con las claves ``'pila'``, ``'entrada'``
            y ``'accion'``, que documenta cada paso del parser.

        Raises:
            SyntaxError: Si la cadena no pertenece al lenguaje generado por
                         la gramática.
        """
        # Asegurar que la entrada termine con $.
        if not tokens or tokens[-1] != END_MARKER:
            tokens = list(tokens) + [END_MARKER]

        log: List[Dict[str, str]] = []
        stack: List[str] = [END_MARKER, self.grammar.start_symbol]
        pos: int = 0

        while stack:
            top: str = stack[-1]
            current: str = tokens[pos] if pos < len(tokens) else END_MARKER

            stack_str: str = " ".join(reversed(stack))
            input_str: str = " ".join(tokens[pos:])

            if top == END_MARKER:
                if current == END_MARKER:
                    log.append({
                        "pila": stack_str,
                        "entrada": input_str,
                        "accion": "✓ Cadena ACEPTADA",
                    })
                    stack.pop()
                else:
                    log.append({
                        "pila": stack_str,
                        "entrada": input_str,
                        "accion": f"✗ Error: se esperaba fin de entrada, "
                                  f"se encontró '{current}'",
                    })
                    raise SyntaxError(
                        f"Tokens sobrantes después del análisis: "
                        f"{' '.join(tokens[pos:])}"
                    )

            elif top in self.grammar.terminals:
                # Coincidencia de terminal.
                if top == current:
                    log.append({
                        "pila": stack_str,
                        "entrada": input_str,
                        "accion": f"match '{top}'",
                    })
                    stack.pop()
                    pos += 1
                else:
                    log.append({
                        "pila": stack_str,
                        "entrada": input_str,
                        "accion": f"✗ Error: se esperaba '{top}', "
                                  f"se encontró '{current}'",
                    })
                    raise SyntaxError(
                        f"Token inesperado: se esperaba '{top}', "
                        f"se encontró '{current}'"
                    )

            elif top in self.grammar.non_terminals:
                # Expansión de No Terminal.
                if current in self.table.get(top, {}):
                    production: List[str] = self.table[top][current]
                    prod_str: str = " ".join(production)
                    log.append({
                        "pila": stack_str,
                        "entrada": input_str,
                        "accion": f"aplicar {top} -> {prod_str}",
                    })
                    stack.pop()
                    # Apilar la producción en orden inverso (para que el
                    # primer símbolo quede en el tope).
                    if production != [EPSILON]:
                        for symbol in reversed(production):
                            stack.append(symbol)
                else:
                    log.append({
                        "pila": stack_str,
                        "entrada": input_str,
                        "accion": f"✗ Error: no hay entrada en M[{top}, "
                                  f"{current}]",
                    })
                    raise SyntaxError(
                        f"No hay producción para M[{top}, {current}]. "
                        f"Token inesperado: '{current}'"
                    )
            else:
                raise SyntaxError(
                    f"Símbolo desconocido en la pila: '{top}'"
                )

        return log

    # ── Impresión de la tabla LL(1) ──────────────────────────────────────
    def print_table(self) -> None:
        """Imprime la tabla predictiva LL(1) en formato tabular legible."""
        g: Grammar = self.grammar
        columns: List[str] = sorted(g.terminals) + [END_MARKER]

        # Calcular anchos de columna.
        col_width: int = max(
            len(c) for c in columns
        )
        for nt in g.non_terminals:
            for terminal, prod in self.table.get(nt, {}).items():
                entry: str = f"{nt} -> {' '.join(prod)}"
                col_width = max(col_width, len(entry))
        col_width += 2

        nt_width: int = max(len(nt) for nt in g.non_terminals) + 2

        # Encabezado.
        header: str = " " * nt_width + "|"
        for col in columns:
            header += f" {col:^{col_width}} |"
        separator: str = "-" * len(header)

        print(separator)
        print("  TABLA PREDICTIVA LL(1)")
        print(separator)
        print(header)
        print(separator)

        for nt in self.grammar._ordered_nonterminals():
            row: str = f" {nt:<{nt_width - 1}}|"
            for col in columns:
                if col in self.table.get(nt, {}):
                    prod: List[str] = self.table[nt][col]
                    cell: str = f"{nt} -> {' '.join(prod)}"
                else:
                    cell = ""
                row += f" {cell:^{col_width}} |"
            print(row)

        print(separator)


# ─────────────────────────────────────────────────────────────────────────────
# Parser de Descenso Recursivo (genérico, guiado por tabla LL(1))
# ─────────────────────────────────────────────────────────────────────────────

class RecursiveDescentParser:
    """Simulación de un parser de descenso recursivo genérico.

    Para evitar problemas de recursividad izquierda y la necesidad de
    codificar a mano cada procedimiento, esta implementación utiliza la
    tabla LL(1) como oráculo de selección de producciones, reproduciendo
    el patrón de llamadas recursivas que se haría manualmente.

    El resultado es un log de llamadas que muestra la traza de invocaciones
    a cada procedimiento del descenso recursivo, incluyendo indentación para
    reflejar la profundidad de la pila de llamadas.

    Atributos públicos:
        grammar : Grammar         — Gramática subyacente.
        table   : dict             — Tabla LL(1) (del LL1Parser).
        tokens  : list[str]        — Cadena de entrada tokenizada.
        pos     : int              — Posición actual en la entrada.
        log     : list[dict]       — Traza de llamadas recursivas.
    """

    def __init__(self, grammar: Grammar, tokens: List[str]) -> None:
        """Inicializa el parser de descenso recursivo.

        Args:
            grammar: Objeto Grammar ya construido.
            tokens:  Lista de tokens de entrada (debe terminar con '$').
        """
        self.grammar: Grammar = grammar

        # Construir la tabla LL(1) como oráculo.
        ll1: LL1Parser = LL1Parser(grammar)
        self.table: Dict[str, Dict[str, List[str]]] = ll1.table

        # Preparar entrada.
        if not tokens or tokens[-1] != END_MARKER:
            self.tokens = list(tokens) + [END_MARKER]
        else:
            self.tokens = list(tokens)

        self.pos: int = 0
        self.log: List[Dict[str, Any]] = []

    # ── Punto de entrada ─────────────────────────────────────────────────
    def parse(self) -> List[Dict[str, Any]]:
        """Ejecuta el análisis por descenso recursivo.

        Returns:
            Lista de diccionarios con las claves ``'profundidad'``,
            ``'procedimiento'``, ``'accion'`` y ``'entrada_restante'``.

        Raises:
            SyntaxError: Si la cadena no pertenece al lenguaje.
        """
        self.pos = 0
        self.log = []
        self._call(self.grammar.start_symbol, depth=0)

        if self.tokens[self.pos] != END_MARKER:
            raise SyntaxError(
                f"Tokens sobrantes después del análisis: "
                f"{' '.join(self.tokens[self.pos:])}"
            )

        self.log.append({
            "profundidad": 0,
            "procedimiento": "—",
            "accion": "✓ Cadena ACEPTADA",
            "entrada_restante": END_MARKER,
        })

        return self.log

    # ── Llamada recursiva genérica ───────────────────────────────────────
    def _call(self, symbol: str, depth: int) -> None:
        """Simula la llamada al procedimiento del No Terminal *symbol*.

        Si *symbol* es un terminal, intenta hacer match.
        Si es un No Terminal, consulta la tabla LL(1) para seleccionar la
        producción y llama recursivamente a cada símbolo del cuerpo.

        Args:
            symbol: Símbolo a procesar (terminal o No Terminal).
            depth:  Profundidad actual en el árbol de llamadas.
        """
        current: str = (
            self.tokens[self.pos] if self.pos < len(self.tokens) else END_MARKER
        )
        remaining: str = " ".join(self.tokens[self.pos:])

        if symbol in self.grammar.terminals:
            # Terminal: match directo.
            if symbol == current:
                self.log.append({
                    "profundidad": depth,
                    "procedimiento": f"match('{symbol}')",
                    "accion": f"match '{symbol}' con entrada '{current}'",
                    "entrada_restante": remaining,
                })
                self.pos += 1
            else:
                raise SyntaxError(
                    f"Descenso recursivo: se esperaba '{symbol}', "
                    f"se encontró '{current}'"
                )
            return

        if symbol not in self.grammar.non_terminals:
            raise SyntaxError(f"Símbolo desconocido: '{symbol}'")

        # No Terminal: seleccionar producción via tabla LL(1).
        if current not in self.table.get(symbol, {}):
            raise SyntaxError(
                f"Descenso recursivo: no hay producción para "
                f"({symbol}, {current})"
            )

        production: List[str] = self.table[symbol][current]
        prod_str: str = " ".join(production)

        self.log.append({
            "profundidad": depth,
            "procedimiento": f"proc_{symbol}()",
            "accion": f"expandir {symbol} -> {prod_str}",
            "entrada_restante": remaining,
        })

        # Llamar recursivamente a cada símbolo de la producción.
        if production != [EPSILON]:
            for child in production:
                self._call(child, depth + 1)

    # ── Impresión del log ────────────────────────────────────────────────
    def print_log(self) -> None:
        """Imprime la traza de llamadas del descenso recursivo con
        indentación visual para reflejar la profundidad."""
        header: str = "=" * 70
        print(header)
        print("  TRAZA DE DESCENSO RECURSIVO")
        print(header)

        for entry in self.log:
            indent: str = "  " * entry["profundidad"]
            proc: str = entry["procedimiento"]
            action: str = entry["accion"]
            remaining: str = entry["entrada_restante"]
            print(f"  {indent}{proc:<30s} | {action:<35s} | {remaining}")

        print(header)


# ─────────────────────────────────────────────────────────────────────────────
# Bloque de verificación
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # ── Gramática de ejemplo ─────────────────────────────────────────────
    sample_grammar: str = r"""
        E  -> T E'
        E' -> + T E' | epsilon
        T  -> F T'
        T' -> * F T' | epsilon
        F  -> ( E ) | id
    """

    g: Grammar = Grammar(sample_grammar)

    # ── Parser LL(1) ─────────────────────────────────────────────────────
    print("=" * 70)
    print("  PARSER LL(1) — ANÁLISIS PREDICTIVO DIRIGIDO POR TABLA")
    print("=" * 70)
    print()

    ll1: LL1Parser = LL1Parser(g)
    ll1.print_table()
    print()

    # Cadena de prueba.
    input_tokens: List[str] = ["id", "+", "id", "$"]
    print(f"  Entrada: {' '.join(input_tokens)}")
    print()

    log: List[Dict[str, str]] = ll1.parse(input_tokens)

    # Imprimir log paso a paso.
    col_pila: int = max(len(entry["pila"]) for entry in log) + 2
    col_entrada: int = max(len(entry["entrada"]) for entry in log) + 2
    separator: str = "-" * (col_pila + col_entrada + 40)

    print(separator)
    print(
        f"  {'PILA':<{col_pila}} | "
        f"{'ENTRADA':<{col_entrada}} | "
        f"ACCIÓN"
    )
    print(separator)

    for entry in log:
        print(
            f"  {entry['pila']:<{col_pila}} | "
            f"  {entry['entrada']:<{col_entrada}} | "
            f"  {entry['accion']}"
        )

    print(separator)

    # ── Parser de Descenso Recursivo ─────────────────────────────────────
    print()
    print()
    rdp: RecursiveDescentParser = RecursiveDescentParser(g, input_tokens)
    rdp.parse()
    rdp.print_log()
