import re
from collections import namedtuple


class LexerException(Exception):
    pass


LexerToken = namedtuple("LexerToken", ["name", "pattern", "value", "ignore"], defaults=(lambda x: None, False))

TokenType = namedtuple("TokenType", ["name", "regex", "value", "ignore"])
Token = namedtuple("Token", ["name", "pos", "value"], defaults=(None,))
LexerMatch = namedtuple("LexerMatch", ["type", "length", "match"])


class Lexer:
    def __init__(self, tokens):
        self.tokens = []
        for token in tokens:
            self.tokens.append(TokenType(token.name, re.compile(token.pattern), token.value, token.ignore))
        self.eof = TokenType("eof", None, None, None)

    def next(self, data, index):
        best = None
        for token in self.tokens:
            match = token.regex.match(data, pos=index)
            if match is None:
                continue
            length = match.end() - match.start()
            if best is None or best.length <= length:   # if length equal, accept last match
                best = LexerMatch(token, length, match)
        if best is None:
            raise LexerException("Lexer error:\n  %s\n  %s^" % (data, " " * index))
        return best

    def lex(self, data):
        index = 0
        tokens = []
        while True:
            match = self.next(data, index)
            if not match.type.ignore:
                value = match.type.value(match.match.group(0))
                tokens.append(Token(match.type.name, match.match.start(), value))
            index = match.match.end()
            if index == len(data):
                tokens.append(Token(self.eof.name, index))
                return tokens
