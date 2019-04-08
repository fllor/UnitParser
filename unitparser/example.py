#!/usr/bin/env python3

import unitparser


reference_length1 = unitparser.parse("nm")
reference_length2 = unitparser.parse("5 Angstrom")

# add and print internal representation
reference_length = reference_length1 + reference_length2
print(reference_length)

# express unit in terms of reference unit
input_length = unitparser.parse("200sqrt(nN/EPa)")
number = unitparser.in_units_of(input_length, reference_length)
print(number)

# add custom function
unitparser.add_function("times_three", lambda x: 3*x, 1, True)

# input loop
while True:
    input_length = input("Enter length: ")

    try:
        number = unitparser.in_units_of(input_length, reference_length)
        print(number)
    except unitparser.UnitException:
        print("Invalid length")
