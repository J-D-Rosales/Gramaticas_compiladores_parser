"""
bottom_up.py — Parsers ascendentes (Bottom-Up) SLR(1), LR(1) y LALR(1).

Implementación basada estrictamente en las definiciones teóricas del
"Libro del Dragón" (Compilers: Principles, Techniques, and Tools)
de Aho, Sethi y Ullman.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Set, Tuple

from grammar import EPSILON, END_MARKER, Grammar


# ─────────────────────────────────────────────────────────────────────────────
# Elementos LR(0) y LR(1)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LR0Item:
    """Representa un elemento LR(0) de la forma A -> α . β
    
    Es inmutable (frozen=True) para poder almacenarlo en conjuntos (Set)
    y utilizarlo como clave o calcular su hash automáticamente.
    """
    lhs: str
    rhs: Tuple[str, ...]
    dot: int

    def __str__(self) -> str:
        rhs_list = list(self.rhs)
        rhs_list.insert(self.dot, ".")
        if not self.rhs:  # Producción epsilon
            rhs_list = ["."]
        return f"{self.lhs} -> {' '.join(rhs_list)}"


@dataclass(frozen=True)
class LR1Item:
    """Representa un elemento LR(1) de la forma [A -> α . β, a]
    
    Un único lookahead (string) garantiza la ausencia de bugs con objetos
    mutables y respeta la definición atómica del Libro del Dragón.
    """
    lhs: str
    rhs: Tuple[str, ...]
    dot: int
    lookahead: str

    def __str__(self) -> str:
        rhs_list = list(self.rhs)
        rhs_list.insert(self.dot, ".")
        if not self.rhs:
            rhs_list = ["."]
        return f"[{self.lhs} -> {' '.join(rhs_list)}, {self.lookahead}]"


# ─────────────────────────────────────────────────────────────────────────────
# Parser SLR(1)
# ─────────────────────────────────────────────────────────────────────────────

class SLR1Parser:
    """Parser ascendente SLR(1) dirigido por tabla."""

    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self.terminals = self.grammar.terminals

        # Crear símbolo inicial aumentado (ej. E') que no exista previamente.
        self.augmented_start = self.grammar.start_symbol + "'"
        while self.augmented_start in self.grammar.non_terminals:
            self.augmented_start += "'"
            
        self.non_terminals = self.grammar.non_terminals | {self.augmented_start}

        # Indexar producciones para asignarles un número (ej. R2).
        self.indexed_productions: List[Tuple[str, Tuple[str, ...]]] = []
        
        # Producción 0: Start' -> Start
        self.indexed_productions.append((self.augmented_start, (self.grammar.start_symbol,)))
        
        for nt in self.grammar._ordered_nonterminals():
            for prod in self.grammar.productions[nt]:
                rhs = () if prod == [EPSILON] else tuple(prod)
                if (nt, rhs) not in self.indexed_productions:
                    self.indexed_productions.append((nt, rhs))

        # Estructuras base
        self.states: List[Any] = []
        self.transitions: Dict[int, Dict[str, int]] = {}
        self.action_table: Dict[int, Dict[str, str]] = {}
        self.goto_table: Dict[int, Dict[str, int]] = {}

        # Construcción invocada al instanciar (aplica también a clases hijas)
        self.build_automaton()
        self.build_tables()

    def closure(self, items: Set[LR0Item]) -> FrozenSet[LR0Item]:
        closure_set = set(items)
        changed = True
        
        while changed:
            changed = False
            new_items = set()
            for item in closure_set:
                if item.dot < len(item.rhs):
                    symbol = item.rhs[item.dot]
                    if symbol in self.grammar.non_terminals:
                        for prod in self.grammar.productions[symbol]:
                            rhs = () if prod == [EPSILON] else tuple(prod)
                            new_item = LR0Item(symbol, rhs, 0)
                            if new_item not in closure_set and new_item not in new_items:
                                new_items.add(new_item)
            if new_items:
                closure_set.update(new_items)
                changed = True
                
        return frozenset(closure_set)

    def goto(self, items: FrozenSet[LR0Item], symbol: str) -> FrozenSet[LR0Item]:
        moved_items = set()
        for item in items:
            if item.dot < len(item.rhs) and item.rhs[item.dot] == symbol:
                moved_items.add(LR0Item(item.lhs, item.rhs, item.dot + 1))
        return self.closure(moved_items)

    def build_automaton(self) -> None:
        start_item = LR0Item(self.augmented_start, (self.grammar.start_symbol,), 0)
        start_state = self.closure({start_item})
        
        self.states = [start_state]
        self.transitions = {0: {}}
        queue = [0]
        
        symbols = self.terminals | self.grammar.non_terminals
        
        while queue:
            current_state_idx = queue.pop(0)
            current_state = self.states[current_state_idx]
            
            for symbol in symbols:
                next_state = self.goto(current_state, symbol)
                if next_state:
                    if next_state not in self.states:
                        self.states.append(next_state)
                        next_state_idx = len(self.states) - 1
                        self.transitions[next_state_idx] = {}
                        queue.append(next_state_idx)
                    else:
                        next_state_idx = self.states.index(next_state)
                    
                    self.transitions[current_state_idx][symbol] = next_state_idx

    def build_tables(self) -> None:
        for i in range(len(self.states)):
            self.action_table[i] = {}
            self.goto_table[i] = {}
            
        for i, state in enumerate(self.states):
            for item in state:
                if item.dot == len(item.rhs):
                    if item.lhs == self.augmented_start:
                        self._add_action(i, END_MARKER, 'ACC')
                    else:
                        prod_idx = self.indexed_productions.index((item.lhs, item.rhs))
                        action_str = f"R{prod_idx}"
                        for a in self.grammar.follow[item.lhs]:
                            self._add_action(i, a, action_str)
                else:
                    a = item.rhs[item.dot]
                    if a in self.terminals:
                        if a in self.transitions.get(i, {}):
                            j = self.transitions[i][a]
                            self._add_action(i, a, f"S{j}")
                            
            for a in self.grammar.non_terminals:
                if a in self.transitions.get(i, {}):
                    self.goto_table[i][a] = self.transitions[i][a]

    def _add_action(self, state: int, symbol: str, action: str) -> None:
        if symbol in self.action_table[state]:
            existing = self.action_table[state][symbol]
            if existing != action:
                parser_name = self.__class__.__name__.replace("Parser", "")
                raise ValueError(
                    f"Conflicto en la tabla ACTION (Estado {state}, Símbolo '{symbol}'): "
                    f"ya existe '{existing}', se intentó agregar '{action}'. "
                    f"La gramática NO es {parser_name}."
                )
        else:
            self.action_table[state][symbol] = action

    def parse(self, tokens: List[str]) -> List[Dict[str, str]]:
        if not tokens or tokens[-1] != END_MARKER:
            tokens = list(tokens) + [END_MARKER]
            
        stack: List[int] = [0]
        sym_stack: List[str] = []
        pos: int = 0
        log: List[Dict[str, str]] = []
        
        while True:
            state = stack[-1]
            current = tokens[pos] if pos < len(tokens) else END_MARKER
            
            formatted_stack = str(stack[0])
            for sym, st in zip(sym_stack, stack[1:]):
                formatted_stack += f" {sym} {st}"
                
            input_str = " ".join(tokens[pos:])
            
            action = self.action_table[state].get(current)
            
            if not action:
                log.append({
                    "pila": formatted_stack,
                    "entrada": input_str,
                    "accion": f"✗ Error sintáctico en estado {state} con '{current}'"
                })
                raise SyntaxError(f"Error sintáctico en el estado {state} con token '{current}'")
                
            if action == 'ACC':
                log.append({
                    "pila": formatted_stack,
                    "entrada": input_str,
                    "accion": "✓ Cadena ACEPTADA"
                })
                break
            elif action.startswith('S'):
                log.append({
                    "pila": formatted_stack,
                    "entrada": input_str,
                    "accion": f"Shift al estado {action[1:]}"
                })
                next_state = int(action[1:])
                stack.append(next_state)
                sym_stack.append(current)
                pos += 1
            elif action.startswith('R'):
                prod_idx = int(action[1:])
                lhs, rhs = self.indexed_productions[prod_idx]
                rhs_str = " ".join(rhs) if rhs else EPSILON
                
                log.append({
                    "pila": formatted_stack,
                    "entrada": input_str,
                    "accion": f"Reduce por {lhs} -> {rhs_str} ({action})"
                })
                
                num_pop = len(rhs)
                if num_pop > 0:
                    stack = stack[:-num_pop]
                    sym_stack = sym_stack[:-num_pop]
                
                top_state = stack[-1]
                if lhs not in self.goto_table[top_state]:
                    raise SyntaxError(
                        f"Error sintáctico: GOTO[{top_state}, {lhs}] indefinido tras reducción."
                    )
                
                next_state = self.goto_table[top_state][lhs]
                stack.append(next_state)
                sym_stack.append(lhs)
                
        return log

    def print_productions(self) -> None:
        """Imprime la lista de producciones numeradas."""
        print("  PRODUCCIONES INDEXADAS")
        print("-" * 55)
        for i, (lhs, rhs) in enumerate(self.indexed_productions):
            rhs_str = " ".join(rhs) if rhs else EPSILON
            print(f"  ({i}) {lhs} -> {rhs_str}")
        print("-" * 55)

    def print_tables(self) -> None:
        """Imprime las tablas ACTION y GOTO en formato tabular."""
        terminals = sorted(self.terminals) + [END_MARKER]
        non_terminals = [nt for nt in self.grammar._ordered_nonterminals() if nt != self.augmented_start]
        
        col_width = max((len(t) for t in terminals), default=0)
        col_width = max(col_width, max((len(nt) for nt in non_terminals), default=0))
        for state in self.action_table:
            for act in self.action_table[state].values():
                col_width = max(col_width, len(act))
        col_width += 2
        
        state_width = max(len(str(len(self.states))), 6)
        
        header_action = " | ".join(f"{t:^{col_width}}" for t in terminals)
        header_goto = " | ".join(f"{nt:^{col_width}}" for nt in non_terminals)
        header = f"{'Estado':^{state_width}} | {header_action} || {header_goto}"
        separator = "-" * len(header)
        
        print(separator)
        parser_name = self.__class__.__name__.replace("Parser", "")
        print(f"{f'TABLAS {parser_name}':^{len(header)}}")
        print(separator)
        print(header)
        print(separator)
        
        for i in range(len(self.states)):
            row_action = " | ".join(f"{self.action_table[i].get(t, ''):^{col_width}}" for t in terminals)
            row_goto = " | ".join(f"{str(self.goto_table[i].get(nt, '')):^{col_width}}" for nt in non_terminals)
            print(f"{i:^{state_width}} | {row_action} || {row_goto}")
            
        print(separator)


# ─────────────────────────────────────────────────────────────────────────────
# Parser LR(1) Canónico
# ─────────────────────────────────────────────────────────────────────────────

class LR1Parser(SLR1Parser):
    """Parser ascendente LR(1) Canónico."""

    def closure(self, items: Set[LR1Item]) -> FrozenSet[LR1Item]:
        closure_set = set(items)
        changed = True
        
        while changed:
            changed = False
            new_items = set()
            for item in closure_set:
                if item.dot < len(item.rhs):
                    B = item.rhs[item.dot]
                    if B in self.grammar.non_terminals:
                        beta = list(item.rhs[item.dot + 1:])
                        beta_a = beta + [item.lookahead]
                        
                        # Cálculo robusto y local de FIRST(beta_a) para evitar limitaciones con el END_MARKER
                        first_beta_a = set()
                        all_have_epsilon = True
                        for sym in beta_a:
                            if sym == EPSILON:
                                first_beta_a.add(EPSILON)
                                break
                            elif sym in self.grammar.non_terminals:
                                first_beta_a.update(self.grammar.first[sym] - {EPSILON})
                                if EPSILON not in self.grammar.first[sym]:
                                    all_have_epsilon = False
                                    break
                            else:
                                first_beta_a.add(sym)
                                all_have_epsilon = False
                                break
                        if all_have_epsilon and beta_a:
                            first_beta_a.add(EPSILON)
                        
                        for prod in self.grammar.productions[B]:
                            rhs = () if prod == [EPSILON] else tuple(prod)
                            for b in first_beta_a:
                                if b != EPSILON:
                                    new_item = LR1Item(B, rhs, 0, b)
                                    if new_item not in closure_set and new_item not in new_items:
                                        new_items.add(new_item)
            if new_items:
                closure_set.update(new_items)
                changed = True
                
        return frozenset(closure_set)

    def goto(self, items: FrozenSet[LR1Item], symbol: str) -> FrozenSet[LR1Item]:
        moved_items = set()
        for item in items:
            if item.dot < len(item.rhs) and item.rhs[item.dot] == symbol:
                moved_items.add(LR1Item(item.lhs, item.rhs, item.dot + 1, item.lookahead))
        return self.closure(moved_items)

    def build_automaton(self) -> None:
        start_item = LR1Item(self.augmented_start, (self.grammar.start_symbol,), 0, END_MARKER)
        start_state = self.closure({start_item})
        
        self.states = [start_state]
        self.transitions = {0: {}}
        queue = [0]
        
        symbols = self.terminals | self.grammar.non_terminals
        
        while queue:
            current_state_idx = queue.pop(0)
            current_state = self.states[current_state_idx]
            
            for symbol in symbols:
                next_state = self.goto(current_state, symbol)
                if next_state:
                    if next_state not in self.states:
                        self.states.append(next_state)
                        next_state_idx = len(self.states) - 1
                        self.transitions[next_state_idx] = {}
                        queue.append(next_state_idx)
                    else:
                        next_state_idx = self.states.index(next_state)
                    
                    self.transitions[current_state_idx][symbol] = next_state_idx

    def build_tables(self) -> None:
        for i in range(len(self.states)):
            self.action_table[i] = {}
            self.goto_table[i] = {}
            
        for i, state in enumerate(self.states):
            for item in state:
                if item.dot == len(item.rhs):
                    if item.lhs == self.augmented_start and item.lookahead == END_MARKER:
                        self._add_action(i, END_MARKER, 'ACC')
                    elif item.lhs != self.augmented_start:
                        prod_idx = self.indexed_productions.index((item.lhs, item.rhs))
                        action_str = f"R{prod_idx}"
                        self._add_action(i, item.lookahead, action_str)
                else:
                    a = item.rhs[item.dot]
                    if a in self.terminals:
                        if a in self.transitions.get(i, {}):
                            j = self.transitions[i][a]
                            self._add_action(i, a, f"S{j}")
                            
            for a in self.grammar.non_terminals:
                if a in self.transitions.get(i, {}):
                    self.goto_table[i][a] = self.transitions[i][a]


# ─────────────────────────────────────────────────────────────────────────────
# Parser LALR(1)
# ─────────────────────────────────────────────────────────────────────────────

class LALR1Parser(LR1Parser):
    """Parser ascendente LALR(1).

    Hereda de LR1Parser. Construye el autómata LR(1) y luego fusiona los
    estados que tienen el mismo núcleo (core LR0).
    """

    def build_automaton(self) -> None:
        super().build_automaton()
        
        cores: List[FrozenSet[LR0Item]] = []
        state_mapping: Dict[int, int] = {}
        merged_states_items: Dict[int, Set[LR1Item]] = {}
        
        def get_core(state: FrozenSet[LR1Item]) -> FrozenSet[LR0Item]:
            return frozenset(LR0Item(item.lhs, item.rhs, item.dot) for item in state)
            
        for i, state in enumerate(self.states):
            core = get_core(state)
            if core not in cores:
                cores.append(core)
                new_idx = len(cores) - 1
                state_mapping[i] = new_idx
                merged_states_items[new_idx] = set(state)
            else:
                new_idx = cores.index(core)
                state_mapping[i] = new_idx
                merged_states_items[new_idx].update(state)
                
        new_states: List[FrozenSet[LR1Item]] = []
        for i in range(len(cores)):
            new_states.append(frozenset(merged_states_items[i]))
            
        new_transitions = {i: {} for i in range(len(new_states))}
        for i, trans in self.transitions.items():
            new_i = state_mapping[i]
            for symbol, j in trans.items():
                new_j = state_mapping[j]
                new_transitions[new_i][symbol] = new_j
                
        self.states = new_states
        self.transitions = new_transitions