"""
Mappers module for transforming raw extracted data to Ulpiano schemas.
"""

from .dni_to_person import map_dni_to_person
from .nota_simple_to_inmueble import map_nota_simple_to_inmueble

__all__ = ["map_dni_to_person", "map_nota_simple_to_inmueble"]
