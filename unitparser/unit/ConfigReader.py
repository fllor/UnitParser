import os
import re
import json
from fractions import Fraction
from collections import namedtuple, OrderedDict
from unitparser.unit.NumberWithUnit import NumberWithUnit, UnitException

BaseUnit = namedtuple("BaseUnit", ["name", "symbol"])
DerivedUnit = namedtuple("DerivedUnit", ["name", "symbol", "value"])
Prefix = namedtuple("Prefix", ["name", "symbol", "value"])
PrefixUnit = namedtuple("PrefixUnit", ["prefix", "unit"])
Constant = namedtuple("Constant", ["name", "symbol", "value"])
UnitFunction = namedtuple("UnitFunction", ["name", "function", "num_args", "unitless"])


class ConfigReader:
    def __init__(self, path):
        with open(path) as f:
            self.data = json.load(f)

        self.base_units = [BaseUnit(*val) for val in self.data["base units"]]
        self.prefixes = [Prefix(*val) for val in self.data["prefixes"]]
        self.num_base_units = len(self.base_units)
        self.prefixes.append(Prefix(None, "", 1))

        self.units = OrderedDict()
        for pre in self.prefixes:
            for unit in self.base_units:
                self.add_unit(pre, unit)

        self.derived_units = None
        self.constants = None
        self.unit_list = list(self.units.keys())

        self.functions = {}

    def load_derived_units(self, parse):
        self.derived_units = [DerivedUnit(val[0], val[1], parse(val[2])) for val in self.data["derived units"]]
        for pre in self.prefixes:
            for unit in self.derived_units:
                self.add_unit(pre, unit)

    def load_constants(self, parse):
        self.constants = [Constant(val[0], val[1], parse(val[2])) for val in self.data["constants"]]
        for const in self.constants:
            self.add_unit(self.prefixes[-1], const)

    def finalize(self):
        for new, old in self.data["synonyms"].items():
            self.units[new] = self.units[old]
        for remove in self.data["remove"]:
            self.units.pop(remove)
        self.unit_list = list(self.units.keys())

    def add_unit(self, prefix, unit):
        key = prefix.symbol + unit.symbol
        if key in self.units:
            ex = self.units[key]
            raise Exception("Conflict between units: " +
                            f"{prefix.name}{unit.name.lower()} and {ex.prefix.name}{ex.unit.name.lower()}")
        self.units[key] = PrefixUnit(prefix, unit)

    def add_function(self, name, apply, num_args, unitless):
        self.functions[name] = UnitFunction(name, apply, num_args, unitless)

    def apply_function(self, name, args):
        func = self.functions[name]
        if func.num_args != len(args):
            raise Exception("Wrong number of argument for function {name}")
        if func.unitless:
            for i, arg in enumerate(args):
                if not arg.is_unitless():
                    raise UnitException(f"Argument for {name} has to be unitless")
                args[i] = arg.num
        result = func.function(*args)
        if isinstance(result, (int, float, Fraction)):
            return NumberWithUnit.from_num(result, self)
        return result

    """ finds all decompositions of a given string into unit, eg "Vs" -> ["V","s"] """
    def find_decomposition(self, data):
        if len(data) == 0:
            return [[]]
        matches = []
        for unit in self.unit_list:
            if data.startswith(unit):
                for match in self.find_decomposition(data[len(unit):]):
                    matches.append([unit] + match)
        return matches
