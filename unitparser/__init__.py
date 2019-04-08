from unitparser.parser.Lexer import LexerException
from unitparser.parser.Parser import ParserException
from unitparser.unit.UnitParser import UnitParser
from unitparser.unit.NumberWithUnit import UnitException


__unit_parser = None


""" initialize parser,
only necessary when using nonstandard config file """
def init(path=None):
    global __unit_parser
    if __unit_parser is None:
        __unit_parser = UnitParser(path)


""" parse string and return internal representation """
def parse(data, debug=False):
    return _get_parser().parse(data, debug=debug)


""" express 'value' in units of 'reference',
both can be either a string or and object constructed py 'parse',
if the arguments don't have the same unit, an exception will be raised """
def in_units_of(value, reference):
    if isinstance(value, str):
        value = parse(value)
    if isinstance(reference, str):
        reference = parse(reference)

    result = value / reference
    if not result.is_unitless():
        raise UnitException(f"Cannot express {str(value)} in units of {str(reference)}")

    return result.num


""" add a function to the parser,
a unitless function will receive numerical arguments, otherwise
the function has to accept and return an internal representation """
def add_function(name, function, num_args, unitless):
    _get_parser().cfg.add_function(name, function, num_args, unitless)
    _get_parser().update_functions()


""" get the parser object, usually not necessary """
def _get_parser():
    init()
    return __unit_parser