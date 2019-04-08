import os
import re
import math
from unitparser.parser.Lexer import Lexer, LexerToken, TokenType
from unitparser.parser.Parser import Parser, GrammarRule
from unitparser.unit import ConfigReader
from unitparser.unit.NumberWithUnit import NumberWithUnit


class UnitParser:
    def __init__(self, path=None):
        if path is None:
            from unitparser import unit
            path = os.path.join(unit.__path__[0], "config.json")

        lexer_tokens = [
            LexerToken("num",   "(?:(?:[1-9][0-9]*|0)(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[1-9][0-9]*)?", float),
            LexerToken("id",    "[a-zA-Z][a-zA-Z0-9]*", str),
            LexerToken("open",  "\\("),
            LexerToken("close", "\\)"),
            LexerToken("add",   "\\+|\\-", lambda x: x == "+"),
            LexerToken("mul",   "\\*|/", lambda x: x == "*"),
            LexerToken("pow",   "\\*\\*|\\^"),
            LexerToken("comma", ","),
            LexerToken("func",  "", str),
            LexerToken("space", " |\t", ignore=True)
        ]

        use_ambiguous_grammar = False

        if use_ambiguous_grammar:
            # ambiguous grammar with priorities
            grammar_rules = [
                GrammarRule("EXP", "EXP add EXP", lambda e1, op, e2: (e1 + e2) if op else (e1 - e2), 1),
                GrammarRule("EXP", "EXP mul EXP", lambda e1, op, e2: (e1 * e2) if op else (e1 / e2), 2),
                GrammarRule("EXP", "EXP EXP", lambda e1, e2: e1 * e2, 4),
                GrammarRule("EXP", "EXP pow EXP", lambda e1, e2: e1 ** e2, 5),
                GrammarRule("EXP", "add EXP", lambda op, e: e if op else -e, 0),
                GrammarRule("EXP", "num", lambda val: NumberWithUnit.from_num(val, self.cfg), 3),
                GrammarRule("EXP", "id", lambda val: NumberWithUnit.from_unit(val, self.cfg), 3),
                GrammarRule("EXP", "open EXP close", priority=0),
                GrammarRule("EXP", "func open ARGS close", lambda fun, e: self.cfg.apply_function(fun, e), 0),
                GrammarRule("ARGS", "EXP", lambda e: [e]),
                GrammarRule("ARGS", "ARGS comma EXP", lambda e1, e2: e1 + [e2])
            ]
        else:
            # unambiguous grammar
            grammar_rules = [
                GrammarRule("EXP", "EXP1"),
                GrammarRule("EXP", "EXP  add EXP1", lambda e1, op, e2: (e1 + e2) if op else (e1 - e2)),
                GrammarRule("EXP1", "EXP2"),
                GrammarRule("EXP1", "EXP1 mul EXP2", lambda e1, op, e2: (e1 * e2) if op else (e1 / e2)),
                GrammarRule("EXP1", "EXP1 EXP3", lambda e1, e2: e1 * e2),
                GrammarRule("EXP2", "EXP3"),
                GrammarRule("EXP2", "add  EXP3", lambda op, e: e if op else -e),
                GrammarRule("EXP3", "EXP4"),
                GrammarRule("EXP3", "EXP4 pow EXP2", lambda e1, e2: e1 ** e2),
                GrammarRule("EXP4", "num", lambda val: NumberWithUnit.from_num(val, self.cfg)),
                GrammarRule("EXP4", "id", lambda val: NumberWithUnit.from_unit(val, self.cfg)),
                GrammarRule("EXP4", "open EXP close"),
                GrammarRule("EXP4", "func open ARGS close", lambda fun, e: self.cfg.apply_function(fun, e)),
                GrammarRule("ARGS", "EXP", lambda e: [e]),
                GrammarRule("ARGS", "ARGS comma EXP", lambda e1, e2: e1 + [e2])
            ]

        self.lexer = Lexer(lexer_tokens)
        self.parser = Parser(grammar_rules, lexer_tokens)

        self.cfg = ConfigReader.ConfigReader(path)
        self.load_default_functions()
        self.update_functions()
        self.cfg.load_derived_units(self.parse)
        self.cfg.load_constants(self.parse)
        self.cfg.finalize()

    """ load predefined units """
    def load_default_functions(self):
        for func in ["sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "exp"]:
            self.cfg.add_function(func, getattr(math, func), 1, True)

        self.cfg.add_function("ln", math.log, 1, True)
        self.cfg.add_function("log", math.log, 2, True)
        self.cfg.add_function("log2", math.log2, 1, True)
        self.cfg.add_function("log10", math.log10, 1, True)

        self.cfg.add_function("sqrt", lambda x: x**0.5, 1, False)
        self.cfg.add_function("pow", lambda x, y: x ** y, 2, False)

    """ update lexer, after adding new functions """
    def update_functions(self):
        pattern = "|".join(sorted(self.cfg.functions.keys(), key=len, reverse=True))
        for i, token in enumerate(self.lexer.tokens):
            if token.name == "func":
                self.lexer.tokens[i] = TokenType("func", re.compile(pattern), str, False)
                break

    """ parse a string representing a number with unit """
    def parse(self, data, debug=False):
        lex = self.lexer.lex(data)
        return self.parser.parse(lex, debug=debug)
