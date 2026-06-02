"""Domain implementations. Importing this module registers all domains."""
from . import algebra      # noqa: F401  (registers AlgebraDomain)
from . import geometry     # noqa: F401  (registers GeometryDomain)
from . import calculus     # noqa: F401  (registers CalculusDomain)
from . import statistics   # noqa: F401  (registers StatisticsDomain)

from ..domain import all_domains, get_domain, Domain  # noqa: F401
