"""ranktool - unconditional algebraic rank of elliptic curves over Q.

The rank is bracketed from below by explicit rational points and from above by
descent.  When the brackets meet, the rank is proved; nothing about the
Tate-Shafarevich group is ever assumed.
"""

from .curve import Curve, DescentModel, Point, O, to_descent_model
from .descent import two_isogeny_descent
from .height import HeightEngine
from .rank import Certificate, analyse, format_certificate

__all__ = [
    "Curve",
    "DescentModel",
    "Point",
    "O",
    "to_descent_model",
    "two_isogeny_descent",
    "HeightEngine",
    "Certificate",
    "analyse",
    "format_certificate",
]
__version__ = "1.0.0"
