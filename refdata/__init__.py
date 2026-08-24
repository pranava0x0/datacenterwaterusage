"""Curated-reference data layer: loaders, taxonomies, id registry, integrity.

Eight datasets. Seven are curated records that cross-reference each other by
id and therefore live in the registry; the eighth, ``local_actions.json``, is
a mirrored county/city table that nothing points at, so it deliberately stays
out of the registry and the integrity graph (Spec D v1, 2026-08-24).

Extracted from ``dashboard.py`` on 2026-07-25 (plan Spec 0.3). Everything here
is **pure** — no ``streamlit`` import anywhere in the package — so the
Streamlit app, ``build_site.py``, the ``scripts/annotate_*.py`` migrations and
the test suite all share one definition of what the data is and how records
reference each other.

``dashboard.py`` re-exports these names, so ``dashboard.load_legislation`` and
``dashboard.CWA_CASE_TYPE_LABELS`` keep resolving exactly as before.
"""

from refdata.loaders import (  # noqa: F401
    BASE_DIR,
    COMPANY_WATER_CLAIMS_PATH,
    CWA_INVESTIGATIONS_PATH,
    DC_WATER_CONFLICTS_PATH,
    LEGISLATION_PATH,
    LOCAL_ACTIONS_PATH,
    REFERENCE_DIR,
    WATER_AUTHORITIES_PATH,
    WATER_NEWS_PATH,
    WATER_SOLUTIONS_PATH,
    clear_caches,
    file_signature,
    load_company_water_claims,
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_legislation,
    load_local_actions,
    load_water_authorities,
    load_water_news,
    load_water_solutions,
)
from refdata.registry import (  # noqa: F401
    KIND_TABS,
    Ref,
    bill_anchor,
    build_registry,
    case_caption,
    registry_collisions,
    resolve,
)
from refdata.integrity import (  # noqa: F401
    EDGE_TARGET_KINDS,
    asymmetric_claim_case_edges,
    dangling_edges,
    iter_edges,
    miskinded_edges,
)
from refdata.taxonomies import *  # noqa: F401,F403
