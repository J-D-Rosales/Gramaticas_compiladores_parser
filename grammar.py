"""
grammar.py — Módulo de procesamiento de gramáticas libres de contexto.

Implementación basada estrictamente en las definiciones teóricas del
"Libro del Dragón" (Compilers: Principles, Techniques, and Tools)
de Aho, Sethi y Ullman.

Este módulo provee la clase Grammar, que a partir de un string multilinea
con la definición de una gramática, extrae automáticamente:
  - Conjuntos de No Terminales y Terminales.
  - Símbolo Inicial (primer No Terminal definido).
  - Producciones estructuradas como dict[str, list[list[str]]].
  - Conjuntos FIRST y FOLLOW para cada No Terminal.

Convenciones de formato de entrada:
  - Cada línea: LHS -> RHS1 | RHS2 | ...
  - Tokens en el RHS separados estrictamente por espacios.
  - La cadena vacía (ε) se representa con la palabra clave 'epsilon'.
  - El primer No Terminal definido es el símbolo inicial.
"""

from __future__ import annotations

from typing import Dict, List, Set


# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────
EPSILON: str = "epsilon"
END_MARKER: str = "$"
ARROW: str = "->"
PIPE: str = "|"


class Grammar:
    """Representación de una Gramática Libre de Contexto (GLC).

    Atributos públicos:
        non_terminals : set[str]  — Conjunto de símbolos No Terminales.
        terminals     : set[str]  — Conjunto de símbolos Terminales.
        start_symbol  : str       — Símbolo Inicial de la gramática.
        productions   : dict[str, list[list[str]]] — Producciones indexadas
                        por No Terminal.  Cada alternativa es una lista de
                        tokens (strings).
        first         : dict[str, set[str]] — Conjuntos FIRST.
        follow        : dict[str, set[str]] — Conjuntos FOLLOW.
    """

    # ── Constructor ──────────────────────────────────────────────────────
    def __init__(self, grammar_text: str) -> None:
        """Inicializa la gramática a partir de un texto multilinea.

        Args:
            grammar_text: Cadena con la definición de la gramática.
                          Cada línea sigue el formato
                          ``LHS -> alt1_tok1 alt1_tok2 | alt2_tok1 ...``
        """
        self.productions: Dict[str, List[List[str]]] = {}
        self.non_terminals: Set[str] = set()
        self.terminals: Set[str] = set()
        self.start_symbol: str = ""

        self._parse_grammar(grammar_text)
        self._identify_terminals()

        self.first: Dict[str, Set[str]] = self._compute_first()
        self.follow: Dict[str, Set[str]] = self._compute_follow()

    # ── Análisis del texto de la gramática ───────────────────────────────
    def _parse_grammar(self, text: str) -> None:
        """Parsea el texto multilinea y llena *productions*, *non_terminals*
        y *start_symbol*.

        Raises:
            ValueError: Si una línea no contiene el operador ``->``.
        """
        lines: List[str] = [
            line.strip() for line in text.strip().splitlines() if line.strip()
        ]

        for line in lines:
            if ARROW not in line:
                raise ValueError(
                    f"Línea inválida (falta '{ARROW}'): {line!r}"
                )

            lhs, rhs_raw = line.split(ARROW, maxsplit=1)
            lhs = lhs.strip()

            if not lhs:
                raise ValueError(f"No Terminal vacío en la línea: {line!r}")

            # Registrar No Terminal y símbolo inicial (primera aparición).
            if not self.start_symbol:
                self.start_symbol = lhs

            self.non_terminals.add(lhs)

            # Separar alternativas por '|' y tokenizar cada una.
            alternatives: List[List[str]] = []
            for alt in rhs_raw.split(PIPE):
                tokens: List[str] = alt.split()
                if not tokens:
                    raise ValueError(
                        f"Alternativa vacía en la línea: {line!r}"
                    )
                alternatives.append(tokens)

            # Si el No Terminal ya tenía producciones, extender la lista.
            if lhs in self.productions:
                self.productions[lhs].extend(alternatives)
            else:
                self.productions[lhs] = alternatives

    def _identify_terminals(self) -> None:
        """Determina el conjunto de terminales.

        Un terminal es cualquier símbolo que aparece en el lado derecho de
        alguna producción y que **no** pertenece al conjunto de No Terminales
        ni es la palabra clave ``epsilon``.
        """
        for alternatives in self.productions.values():
            for tokens in alternatives:
                for tok in tokens:
                    if tok != EPSILON and tok not in self.non_terminals:
                        self.terminals.add(tok)

    # ── Cálculo de FIRST ─────────────────────────────────────────────────
    def _compute_first(self) -> Dict[str, Set[str]]:
        """Calcula los conjuntos FIRST para todos los No Terminales.

        Algoritmo (Dragon Book, Sección 4.4):
            1. Si X es un terminal, FIRST(X) = {X}.
            2. Si X → epsilon es una producción, agregar epsilon a FIRST(X).
            3. Si X → Y₁ Y₂ … Yₖ es una producción:
               a. Agregar todo lo de FIRST(Y₁) − {epsilon} a FIRST(X).
               b. Si epsilon ∈ FIRST(Y₁), agregar FIRST(Y₂) − {epsilon}, etc.
               c. Si epsilon ∈ FIRST(Yᵢ) para todo i = 1..k, agregar epsilon
                  a FIRST(X).

        El cálculo se itera hasta alcanzar un punto fijo.

        Returns:
            Diccionario que mapea cada No Terminal a su conjunto FIRST.
        """
        first: Dict[str, Set[str]] = {nt: set() for nt in self.non_terminals}

        changed: bool = True
        while changed:
            changed = False
            for nt in self.non_terminals:
                for production in self.productions[nt]:
                    before: int = len(first[nt])
                    self._add_first_of_string(first, production, first[nt])
                    if len(first[nt]) != before:
                        changed = True

        return first

    def _add_first_of_string(
        self,
        first_sets: Dict[str, Set[str]],
        symbols: List[str],
        target: Set[str],
    ) -> None:
        """Agrega FIRST(α) al conjunto *target*, donde α es una cadena de
        símbolos.

        Recorre cada símbolo de *symbols* de izquierda a derecha:
        - Si el símbolo es un terminal, agrega ese terminal y detiene.
        - Si es epsilon, agrega epsilon y detiene.
        - Si es un No Terminal, agrega FIRST(NT) − {epsilon}; si epsilon no
          está en FIRST(NT), detiene.  Si epsilon está, continúa con el
          siguiente símbolo.
        - Si todos los símbolos derivan epsilon, agrega epsilon.
        """
        all_have_epsilon: bool = True

        for sym in symbols:
            if sym == EPSILON:
                # Producción explícita de epsilon.
                target.add(EPSILON)
                return

            if sym in self.terminals:
                target.add(sym)
                all_have_epsilon = False
                break

            # sym es un No Terminal.
            first_of_sym: Set[str] = first_sets.get(sym, set())
            target.update(first_of_sym - {EPSILON})

            if EPSILON not in first_of_sym:
                all_have_epsilon = False
                break

        if all_have_epsilon and symbols:
            target.add(EPSILON)

    # ── Cálculo de FOLLOW ────────────────────────────────────────────────
    def _compute_follow(self) -> Dict[str, Set[str]]:
        """Calcula los conjuntos FOLLOW para todos los No Terminales.

        Algoritmo (Dragon Book, Sección 4.4):
            1. Agregar $ a FOLLOW(S), donde S es el símbolo inicial.
            2. Para cada producción A → α B β:
               a. Agregar FIRST(β) − {epsilon} a FOLLOW(B).
               b. Si β es vacío o epsilon ∈ FIRST(β), agregar FOLLOW(A) a
                  FOLLOW(B).
            3. Repetir hasta alcanzar un punto fijo.

        Returns:
            Diccionario que mapea cada No Terminal a su conjunto FOLLOW.
        """
        follow: Dict[str, Set[str]] = {nt: set() for nt in self.non_terminals}

        # Regla 1: $ ∈ FOLLOW(Start).
        follow[self.start_symbol].add(END_MARKER)

        changed: bool = True
        while changed:
            changed = False
            for nt in self.non_terminals:
                for production in self.productions[nt]:
                    self._update_follow(follow, nt, production, changed_flag=[False])

            # Re-evaluar cambios recorriendo completo con detección explícita.
            changed = self._follow_iteration(follow)
        return follow

    def _follow_iteration(self, follow: Dict[str, Set[str]]) -> bool:
        """Ejecuta una iteración completa de las reglas FOLLOW y devuelve
        True si hubo algún cambio en los conjuntos."""
        changed: bool = False

        for nt in self.non_terminals:
            for production in self.productions[nt]:
                for i, sym in enumerate(production):
                    if sym not in self.non_terminals:
                        continue

                    # β = todo lo que viene después de sym en la producción.
                    beta: List[str] = production[i + 1:]

                    if beta:
                        first_beta: Set[str] = self._first_of_string(beta)

                        # Regla 2a: FIRST(β) − {ε} ⊆ FOLLOW(B)
                        addition: Set[str] = first_beta - {EPSILON}
                        if not addition.issubset(follow[sym]):
                            follow[sym].update(addition)
                            changed = True

                        # Regla 2b: si ε ∈ FIRST(β), FOLLOW(A) ⊆ FOLLOW(B)
                        if EPSILON in first_beta:
                            if not follow[nt].issubset(follow[sym]):
                                follow[sym].update(follow[nt])
                                changed = True
                    else:
                        # β está vacío → Regla 2b directa.
                        if not follow[nt].issubset(follow[sym]):
                            follow[sym].update(follow[nt])
                            changed = True

        return changed

    def _update_follow(
        self,
        follow: Dict[str, Set[str]],
        lhs: str,
        production: List[str],
        changed_flag: List[bool],
    ) -> None:
        """Aplica las reglas FOLLOW para una producción específica.

        (Método auxiliar utilizado internamente por _compute_follow durante
        la primera pasada; la lógica principal de punto fijo reside en
        _follow_iteration.)
        """
        for i, sym in enumerate(production):
            if sym not in self.non_terminals:
                continue

            beta: List[str] = production[i + 1:]

            if beta:
                first_beta: Set[str] = self._first_of_string(beta)
                addition: Set[str] = first_beta - {EPSILON}
                if not addition.issubset(follow[sym]):
                    follow[sym].update(addition)
                    changed_flag[0] = True

                if EPSILON in first_beta:
                    if not follow[lhs].issubset(follow[sym]):
                        follow[sym].update(follow[lhs])
                        changed_flag[0] = True
            else:
                if not follow[lhs].issubset(follow[sym]):
                    follow[sym].update(follow[lhs])
                    changed_flag[0] = True

    def _first_of_string(self, symbols: List[str]) -> Set[str]:
        """Calcula FIRST(α) para una cadena arbitraria de símbolos.

        Utiliza los conjuntos FIRST ya calculados (self.first).

        Args:
            symbols: Lista de tokens que conforman la cadena α.

        Returns:
            Conjunto FIRST de la cadena.
        """
        result: Set[str] = set()
        all_have_epsilon: bool = True

        for sym in symbols:
            if sym == EPSILON:
                result.add(EPSILON)
                return result

            if sym in self.terminals:
                result.add(sym)
                all_have_epsilon = False
                break

            # sym es un No Terminal.
            first_sym: Set[str] = self.first.get(sym, set())
            result.update(first_sym - {EPSILON})

            if EPSILON not in first_sym:
                all_have_epsilon = False
                break

        if all_have_epsilon and symbols:
            result.add(EPSILON)

        return result

    # ── Utilidad pública: FIRST de una cadena arbitraria ─────────────────
    def first_of(self, symbols: List[str]) -> Set[str]:
        """Calcula FIRST para una cadena arbitraria de símbolos gramaticales.

        Método de conveniencia para uso externo (por ejemplo, en la
        construcción de tablas de parseo).

        Args:
            symbols: Secuencia de símbolos (terminales/no terminales/epsilon).

        Returns:
            Conjunto FIRST de la cadena.
        """
        return self._first_of_string(symbols)

    # ── Representación legible ───────────────────────────────────────────
    def __repr__(self) -> str:
        lines: List[str] = [f"Grammar(start={self.start_symbol!r})"]
        for nt in self._ordered_nonterminals():
            alts: List[str] = [
                " ".join(prod) for prod in self.productions[nt]
            ]
            lines.append(f"  {nt} -> {' | '.join(alts)}")
        return "\n".join(lines)

    def _ordered_nonterminals(self) -> List[str]:
        """Devuelve los No Terminales en orden de definición (el símbolo
        inicial primero, luego el resto en el orden en que aparecieron)."""
        seen: List[str] = []
        # Recorrer las claves del diccionario preserva el orden de inserción
        # a partir de Python 3.7+.
        for nt in self.productions:
            if nt not in seen:
                seen.append(nt)
        return seen

    # ── Impresión formateada de FIRST y FOLLOW ───────────────────────────
    def print_first_follow(self) -> None:
        """Imprime de forma ordenada los conjuntos FIRST y FOLLOW de cada
        No Terminal para verificación visual."""
        header: str = "=" * 55
        sub_header: str = "-" * 55

        print(header)
        print("  CONJUNTOS FIRST y FOLLOW")
        print(header)

        for nt in self._ordered_nonterminals():
            first_str: str = ", ".join(sorted(self.first[nt]))
            follow_str: str = ", ".join(sorted(self.follow[nt]))
            print(f"\n  {nt}:")
            print(f"    FIRST  = {{ {first_str} }}")
            print(f"    FOLLOW = {{ {follow_str} }}")

        print(f"\n{sub_header}")
        print(f"  Terminales:     {{ {', '.join(sorted(self.terminals))} }}")
        print(f"  No Terminales:  {{ {', '.join(sorted(self.non_terminals))} }}")
        print(f"  Símbolo Inicial: {self.start_symbol}")
        print(header)


# ─────────────────────────────────────────────────────────────────────────────
# Bloque de verificación
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_grammar: str = r"""
        E  -> T E'
        E' -> + T E' | epsilon
        T  -> F T'
        T' -> * F T' | epsilon
        F  -> ( E ) | id
    """

    g: Grammar = Grammar(sample_grammar)

    print(g)
    print()
    g.print_first_follow()
