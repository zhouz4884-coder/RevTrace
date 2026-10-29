"""Scalar FP32 bit reference for the pinned author's generated median kernel.

This is a component diagnostic reference, not a replacement implementation.
Selections retain the chosen operand's original bits, including NaN payloads
and signed zeros. Ordered comparisons of embedded FP32 values are exact.
"""
import struct


def as_float(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def as_bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def window_network_bits(window):
    """Exactly the author's i/j loop and two independent tl.where choices."""
    width = len(window)
    assert width > 0 and width % 2 == 1
    rows = list(window)
    for i in range(width // 2 + 1):
        for j in range(width - i - 1):
            a, b = rows[j], rows[j + 1]
            # Both comparisons use the pre-update a/b operands. On ties or
            # unordered comparisons, both expressions select operand b.
            smaller = a if as_float(a) < as_float(b) else b
            larger = a if as_float(a) > as_float(b) else b
            rows[j], rows[j + 1] = smaller, larger
    return rows[width // 2]


def filter_network_bits(values, width):
    """Author reflect padding and short-input identity, along one last axis."""
    assert width > 0 and width % 2 == 1
    values = list(values)
    pad = width // 2
    if len(values) <= pad:
        return values
    padded = values[1:pad + 1][::-1] + values
    padded += values[-pad - 1:-1][::-1] if pad else []
    return [window_network_bits(padded[i:i + width]) for i in range(len(values))]


def explain(values, width=7):
    output = filter_network_bits(values, width)
    return dict(input_bits=[f'{v:08x}' for v in values], output_bits=[f'{v:08x}' for v in output],
        output_float=[as_float(v) if as_float(v) == as_float(v) else 'NaN' for v in output])


if __name__ == '__main__':
    import json
    zero = [0x00000000, 0x80000000, 0x00000000, 0x80000000, 0x00000000, 0x80000000, 0x00000000]
    nan = [as_bits(v) for v in [1., .1, .2, .1, .3, .4, .5]]
    nan[1] = 0x7fc00000
    print(json.dumps(dict(signed_zero=explain(zero), nan_payload=explain(nan)), indent=2))
