from fractions import Fraction
from unitparser.unit import ConfigReader


class UnitException(Exception):
    pass


class NumberWithUnit:
    def __init__(self, num, unit, base_units):
        assert isinstance(num, (int, float, Fraction)), f"{num} {type(num)}"
        self.num = num
        self.unit = tuple(unit)
        for u in unit:
            if not isinstance(u, Fraction):
                raise Exception(f"Invalid unit argument: {u}")
        self.base_units = base_units

    @classmethod
    def from_num(cls, num, config):
        return NumberWithUnit(num, (Fraction(0),)*config.num_base_units, config.base_units)

    @classmethod
    def from_unit(cls, unit, config, num=1):
        if unit in config.units:
            match = config.units[unit]
            if isinstance(match.unit, ConfigReader.BaseUnit):
                idx = config.base_units.index(match.unit)
                unit_vec = [Fraction(1 if idx == i else 0) for i in range(config.num_base_units)]
                return NumberWithUnit(num * match.prefix.value, unit_vec, config.base_units)
            if isinstance(match.unit, ConfigReader.DerivedUnit):
                return num * match.prefix.value * match.unit.value
            if isinstance(match.unit, ConfigReader.Constant):
                return num * match.unit.value
            raise NotImplementedError()
        matches = config.find_decomposition(unit)
        if len(matches) == 1:
            ret = NumberWithUnit.from_num(num, config)
            for u in matches[0]:
                ret *= NumberWithUnit.from_unit(u, config)
            return ret
        if len(matches) > 1:
            possible_matches = [" ".join(match) for match in matches]
            raise UnitException(f"Ambiguous unit: {unit}: ({') or ('.join(possible_matches)})")
        raise UnitException("Unknown unit: %s" % unit)

    def __add__(self, other):
        if not isinstance(other, NumberWithUnit):
            raise UnitException("Cannot add unitless number to number with unit")
        if id(self.base_units) != id(other.base_units):
            raise UnitException("Cannot combine numbers with different base units")
        for i in range(len(self.unit)):
            if self.unit[i] != other.unit[i]:
                raise UnitException(f"Cannot add units: {str(self)} + {str(other)}")
        return NumberWithUnit(self.num + other.num, self.unit, self.base_units)

    def __sub__(self, other):
        if not isinstance(other, NumberWithUnit):
            raise UnitException("Cannot subtract unitless number from number with unit")
        if id(self.base_units) != id(other.base_units):
            raise UnitException("Cannot combine numbers with different base units")
        for i in range(len(self.unit)):
            if self.unit[i] != other.unit[i]:
                raise UnitException(f"Cannot subtract units: {str(self)} + {str(other)}")
        return NumberWithUnit(self.num - other.num, self.unit, self.base_units)

    def __mul__(self, other):
        if isinstance(other, NumberWithUnit):
            if id(self.base_units) != id(other.base_units):
                raise Exception("Cannot combine numbers with different base units")
            unit_vec = [self.unit[i] + other.unit[i] for i in range(len(self.unit))]
            return NumberWithUnit(self.num * other.num, unit_vec, self.base_units)
        if isinstance(other, (int, float)):
            return NumberWithUnit(self.num * other, self.unit, self.base_units)
        raise NotImplementedError()

    def __truediv__(self, other):
        if isinstance(other, NumberWithUnit):
            if id(self.base_units) != id(other.base_units):
                raise UnitException("Cannot combine numbers with different base units")
            unit_vec = [self.unit[i] - other.unit[i] for i in range(len(self.unit))]
            return NumberWithUnit(self.num / other.num, unit_vec, self.base_units)
        if isinstance(other, (int, float)):
            return NumberWithUnit(self.num / other, self.unit, self.base_units)
        raise NotImplementedError()

    def __pow__(self, power):
        if isinstance(power, NumberWithUnit):
            if id(self.base_units) != id(power.base_units):
                raise UnitException("Cannot combine numbers with different base units")
            if not power.is_unitless():
                raise UnitException("Cannot use unit in exponent: %s" % power)
            return self.__pow__(power.num)
        if isinstance(power, float):
            power = Fraction(power)
        if isinstance(power, (int, Fraction)):
            unit_vec = [u * power for u in self.unit]
            return NumberWithUnit(self.num ** power, unit_vec, self.base_units)
        raise NotImplementedError()

    def __rmul__(self, other):
        if isinstance(other, (int, float)):
            return NumberWithUnit(self.num * other, self.unit, self.base_units)
        raise NotImplementedError()

    def __rtruediv__(self, other):
        if isinstance(other, (int, float)):
            return NumberWithUnit(other / self.num, [-u for u in self.unit], self.base_units)
        raise NotImplementedError()

    def __neg__(self):
        return NumberWithUnit(-self.num, self.unit, self.base_units)

    def __eq__(self, other):
        if not isinstance(other, NumberWithUnit):
            return False
        if id(self.base_units) != id(other.base_units):
            return False
        for a, b in zip(self.unit, other.unit):
            if a != b:
                return False
        return self.num == other.num

    def __str__(self):
        unit_str = ""
        for i in range(len(self.unit)):
            if self.unit[i].numerator != 0:
                if self.unit[i].numerator == self.unit[i].denominator:
                    unit_str += f" {self.base_units[i].symbol}"
                else:
                    unit_str += f" {self.base_units[i].symbol}^{str(self.unit[i])}"
        return f"{float(self.num):.12g}{unit_str}"

    def __repr__(self):
        units = [str(u) for u in self.unit]
        return f"NumberWithUnit({self.num};{','.join(units)})"

    def is_unitless(self):
        for unit in self.unit:
            if unit.numerator != 0:
                return False
        return True
