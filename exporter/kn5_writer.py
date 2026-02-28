import struct
from typing import BinaryIO, Sequence, Iterable


ENCODING: str = 'utf-8'


class KN5Writer:
    """Base class for writing binary data to Assetto Corsa file formats."""

    def __init__(self, file: BinaryIO):
        self.file: BinaryIO = file

    def write_string(self, string: str):
        """Writes a length-prefixed UTF-8 string."""
        string_bytes: bytes = string.encode(ENCODING)
        self.write_uint(len(string_bytes))
        self.file.write(string_bytes)

    def write_blob(self, blob: bytes):
        """Writes length-prefixed raw bytes."""
        self.write_uint(len(blob))
        self.file.write(blob)

    def write_uint(self, int_val: int):
        """Writes a 32-bit unsigned integer."""
        self.file.write(struct.pack('I', int_val))

    def write_int(self, int_val: int):
        """Writes a 32-bit signed integer."""
        self.file.write(struct.pack('i', int_val))

    def write_ushort(self, short: int):
        """Writes a 16-bit unsigned integer."""
        self.file.write(struct.pack('H', short))

    def write_byte(self, byte: int):
        """Writes an 8-bit unsigned integer."""
        self.file.write(struct.pack('B', byte))

    def write_bool(self, bool_val: bool):
        """Writes a boolean as a single byte."""
        self.file.write(struct.pack('?', bool_val))

    def write_float(self, f: float):
        """Writes a 32-bit float."""
        self.file.write(struct.pack('f', f))

    def write_vector2(self, vector2: Sequence[float]):
        """Writes a pair of 32-bit floats."""
        self.file.write(struct.pack('2f', *vector2))

    def write_vector3(self, vector3: Sequence[float]):
        """Writes three 32-bit floats."""
        self.file.write(struct.pack('3f', *vector3))

    def write_vector4(self, vector4: Sequence[float]):
        """Writes four 32-bit floats."""
        self.file.write(struct.pack('4f', *vector4))

    def write_matrix(self, matrix: Sequence[Sequence[float]]):
        """Writes a 4x4 matrix in column-major order."""
        for row in range(4):
            for col in range(4):
                self.write_float(matrix[col][row])

    def write_list(self, L: Iterable[float]):
        """Writes a flat list of floats."""
        for float_val in L:
            self.write_float(float_val)
