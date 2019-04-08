import sys
from collections import namedtuple
from unitparser.parser import Lexer


class ParserException(Exception):
    pass


GrammarRule = namedtuple("GrammarRule", ["target", "expansion", "value", "priority"], defaults=(lambda x: x, -1))
StackItem = namedtuple("StackItem", ["item", "state"])


class Symbol:
    def __init__(self, name):
        self.name = name
        self.nullable = None
        self.first = None
        self.follow = None

    def __repr__(self):
        return self.__str__()


class Terminal(Symbol):
    def __init__(self, name):
        super().__init__(name)
        self.nullable = False
        self.first = {self}
        self.follow = None

    def __str__(self):
        return f"T({self.name})"


class Nonterminal(Symbol):
    def __init__(self, name):
        super().__init__(name)
        self.nullable = False
        self.first = set()
        self.follow = set()
        self.productions = set()

    def add_production(self, production):
        self.productions.add(production)
        if isinstance(production.expansion[0], Terminal):
            self.first.add(production.expansion[0])

    def update_nullable(self):
        if self.nullable:
            return False
        for prod in self.productions:
            for symbol in prod.expansion:
                if not symbol.nullable:
                    break
            else:
                self.nullable = True
                return True
        return False

    def update_first(self):
        oldlen = len(self.first)
        for prod in self.productions:
            for symbol in prod.expansion:
                self.first.update(symbol.first)
                if not symbol.nullable:
                    break
        return len(self.first) != oldlen

    def __str__(self):
        return f"NT({self.name})"


class Production:
    def __init__(self, rule, parser):
        self.target = parser.nonterminals[rule.target]
        self.expansion = tuple([parser.symbols[x] for x in rule.expansion.split()])
        self.value = rule.value
        self.target.add_production(self)
        self.id = len(parser.productions)
        self.priority = rule.priority

    def apply(self, rhs):
        args = []
        for arg in rhs:
            if isinstance(arg, Lexer.Token):
                if arg.value is not None:
                    args.append(arg.value)
            else:
                args.append(arg)
        return self.value(*args)

    def __repr__(self):
        return f"P({self.id})"

    def __str__(self):
        return repr(self) + f": {str(self.target)} -> {' '.join(map(str, self.expansion))}"


class NFATransition:
    def __init__(self, symbol, target):
        self.symbol = symbol
        self.target = target

    def __str__(self):
        return f"{self.symbol} -> {self.target}"

    def __repr__(self):
        return str(self)


class NFAState:
    def __init__(self, state_id, transition = None, accepting = None):
        self.id = state_id
        self.transitions = set()
        self.accepting = set()
        if transition is not None:
            self.transitions.add(transition)
        if accepting is not None:
            self.accepting.add(accepting)

    def __str__(self):
        return repr(self) + f":  trans=({self.transitions}), acc=({','.join(map(repr, self.accepting))})"

    def __repr__(self):
        return f"NSt({self.id})"


class NFA:
    def __init__(self, parser):
        counter = 0
        self.states = {}
        self.start_state = 0

        start_states = {nonterm: set() for nonterm in parser.nonterminals.values()}
        for prod in parser.productions:
            for i, symbol in enumerate(prod.expansion):
                self.states[counter] = NFAState(counter, NFATransition(symbol, counter + 1))
                if i == 0:
                    start_states[prod.target].add(counter)
                counter += 1
            self.states[counter] = NFAState(counter, accepting=prod)
            counter += 1

        for state in self.states.values():
            for trans in state.transitions.copy():
                if isinstance(trans.symbol, Nonterminal):
                    for target in start_states[trans.symbol]:
                        state.transitions.add(NFATransition("eps", target))

    def closure(self, states):
        assert isinstance(states, tuple)
        closed = list(states)
        i = 0
        while i < len(closed):
            if closed[i] not in closed[:i]:
                for trans in self.states[closed[i]].transitions:    # add targets of all epsilon transitions
                    if trans.symbol == "eps":
                        closed.append(trans.target)
            i += 1
        return tuple(sorted(list(set(closed))))

    def print(self):
        print(f"NFA: start={self.start_state}")
        for state_id in sorted(self.states.keys()):
            print(" ", self.states[state_id])


class DFAState:
    def __init__(self, nfa, dfa, start_state):
        self.id = len(dfa.states)
        self.nfa_states = nfa.closure(start_state)

        self.transitions = {}
        self.accepting = set()

        nd_trans = {}
        for state in self.nfa_states:
            for trans in nfa.states[state].transitions:
                if trans.symbol == "eps":
                    continue
                nd_trans.setdefault(trans.symbol, set()).add(trans.target)
        for sym, transitions in nd_trans.items():
            target_states = nfa.closure(tuple(transitions))
            self.transitions[sym] = target_states
            for state in dfa.states.values():
                if state.nfa_states == target_states:
                    break
            else:
                for state in dfa.pending_states:
                    if state == target_states:
                        break
                else:
                    if target_states != self:
                        dfa.pending_states.append(target_states)
        for state in self.nfa_states:
            for acc in nfa.states[state].accepting:
                self.accepting.add(acc)
        dfa.states[self.id] = self

    def __repr__(self):
        return f"DSt({self.id})"

    def __str__(self):
        return f"{repr(self)} {self.nfa_states} trans=({self.transitions}), acc=({','.join(map(repr, self.accepting))})"


class DFA:
    def __init__(self, nfa):
        self.states = {}
        self.pending_states = []

        DFAState(nfa, self, (nfa.start_state,))
        while len(self.pending_states) > 0:
            DFAState(nfa, self, self.pending_states.pop(0))

        inv_states = {state.nfa_states: state.id for state in self.states.values()}

        for state in self.states.values():
            for sym, target in state.transitions.items():
                state.transitions[sym] = inv_states[state.transitions[sym]]

    def print(self):
        print("DFA:")
        for state_id in sorted(self.states.keys()):
            print(" ", self.states[state_id])


class TableAction:
    pass


class ActionShift(TableAction):
    def __init__(self, target):
        self.target = target

    def __str__(self):
        return f"S{self.target}"


class ActionGoto(TableAction):
    def __init__(self, target):
        self.target = target

    def __str__(self):
        return f"G{self.target}"


class ActionReduce(TableAction):
    def __init__(self, prod):
        self.prod= prod

    def __str__(self):
        return f"R{self.prod}"


class ActionAccept(TableAction):
    def __str__(self):
        return "A"


class ParseTable:
    def __init__(self, dfa, parser):
        self.table_sym = [sym for name, sym in parser.symbols.items() if name not in ("START", "START'")]
        self.data = {state: {sym: None for sym in self.table_sym} for state in dfa.states.keys()}

        for state_id, state in dfa.states.items():
            for sym, target in state.transitions.items():
                assert isinstance(sym, Symbol), sym
                if isinstance(sym, Terminal):
                    self.data[state_id][sym] = ActionShift(target)
                else:
                    self.data[state_id][sym] = ActionGoto(target)
            for prod in state.accepting:
                for sym in prod.target.follow:
                    if prod.id == 0:
                        new_action = ActionAccept()
                    else:
                        new_action = ActionReduce(prod.id)
                    if self.data[state_id][sym] is None or \
                            self.handle_conflict(state_id, sym, new_action, prod, parser):
                        self.data[state_id][sym] = new_action

    def handle_conflict(self, state_id, symbol, action, prod, parser):
        if isinstance(self.data[state_id][symbol], ActionReduce):
            priority_existing = parser.productions[self.data[state_id][symbol].prod].priority
        else:
            productions = set()
            for nfa_state in parser.dfa.states[state_id].nfa_states:
                for trans in parser.nfa.states[nfa_state].transitions:
                    if symbol == trans.symbol:
                        accepting_state = trans.target
                        while len(parser.nfa.states[accepting_state].accepting) == 0:
                            accepting_state += 1
                        productions.update(parser.nfa.states[accepting_state].accepting)
            priority_existing = max((p.priority for p in productions), default=-1)
        priority_new = prod.priority

        if priority_existing == -1 or priority_new == -1:
            msg = f"{state_id}:{symbol} {self.data[state_id][symbol]}, {action}"
            print("Shift-Reduce conflict:", msg, file=sys.stderr)

        if priority_new > priority_existing:
            return True
        if priority_new < priority_existing:
            return False
        return True

    def print(self, parser):
        print("SLR table:")
        print(" " * 9, "\t".join([x.name for x in self.table_sym]).expandtabs(10))
        for i in range(len(parser.dfa.states)):
            row = str(i)
            for sym in self.table_sym:
                if self.data[i][sym] is None:
                    row += "\t-"
                else:
                    row += "\t" + str(self.data[i][sym])
            print(row.expandtabs(10))


class Parser:
    def __init__(self, grammar_rules, lexer_tokens):
        list_of_nonterminals = [rule.target for rule in grammar_rules] + ["START", "START'"]
        self.nonterminals = {name: Nonterminal(name) for name in list_of_nonterminals}
        self.terminals = {token.name: Terminal(token.name) for token in lexer_tokens}
        self.terminals["eof"] = Terminal("eof")
        self.symbols = self.terminals.copy()
        self.symbols.update(self.nonterminals)

        self.productions = []
        self.productions.append(Production(GrammarRule("START", "EXP", None), self))
        for rule in grammar_rules:
            self.productions.append(Production(rule, self))

        self.extended_productions = self.productions + [
            Production(GrammarRule("START'", "START eof", None), self)
        ]

        changed = True
        while changed:
            changed = False
            for nonterm in self.nonterminals.values():
                changed |= nonterm.update_nullable()
        changed = True
        while changed:
            changed = False
            for nonterm in self.nonterminals.values():
                changed |= nonterm.update_first()

        changed = True
        while changed:
            changed = False
            for prod in self.extended_productions:
                for i, symbol in enumerate(prod.expansion):
                    if isinstance(symbol, Terminal):
                        continue
                    oldlen = len(symbol.follow)
                    if len(prod.expansion) > i + 1:
                        symbol.follow.update(prod.expansion[i + 1].first)
                    if prod.target != symbol and all([x.nullable for x in prod.expansion[i + 1:]]):
                        symbol.follow.update(prod.target.follow)
                    changed |= len(symbol.follow) != oldlen

        self.nfa = NFA(self)
        self.dfa = DFA(self.nfa)

        self.table = ParseTable(self.dfa, self)

    def print(self):
        print("Terminals:", self.terminals.values())
        print("Nonterminals:", self.nonterminals.values())
        print("Productions:\n ", "\n  ".join(map(str, self.productions)))
        print("First:")
        for name, nonterm in self.nonterminals.items():
            print(f"  {name}:", *map(str, nonterm.first))
        print("Follow:")
        for name, nonterm in self.nonterminals.items():
            print(f"  {name}:", *map(str, nonterm.follow))
        print()
        self.nfa.print()
        print()
        self.dfa.print()
        print()
        self.table.print(self)

    def parse_single(self, token_list, stack, raw_data=None):
        state = stack[-1].state
        action = self.table.data[state][self.symbols[token_list[0].name]]
        if isinstance(action, ActionShift):
            stack.append(StackItem(token_list.pop(0), action.target))
        elif isinstance(action, ActionReduce):
            prod = self.productions[action.prod]
            num_symbols = len(prod.expansion)
            args = [x for x, y in stack[len(stack) - num_symbols:]]
            item = prod.apply(args)
            del stack[len(stack) - num_symbols:]    # use del, to avoid parameter assignment
            action = self.table.data[stack[-1].state][prod.target]
            assert isinstance(action, ActionGoto), "Invalid parse table"
            stack.append(StackItem(item, action.target))
        elif isinstance(action, ActionAccept):
            return True
        elif action is None:
            if raw_data is None:
                raise ParserException("Syntax error")
            raise ParserException("Syntax error:\n  %s\n  %s^" % (raw_data, " " * token_list[0].pos))
        else:
            raise Exception("Parse error: %s" % action)
        return False

    def parse(self, token_list, raw_data=None, debug=False):
        stack = [StackItem(None, 0)]
        token_list = token_list.copy()

        while not self.parse_single(token_list, stack, raw_data):
            if debug:
                print(stack, token_list)

        return stack[1].item
