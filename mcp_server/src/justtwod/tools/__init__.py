"""Register every tool module with the shared FastMCP instance.

Importing this package triggers `@mcp.tool()` registration as a side effect
for every submodule listed here.
"""
from __future__ import annotations

from . import adjustment  # noqa: F401
from . import canvas  # noqa: F401
from . import core  # noqa: F401
from . import document  # noqa: F401
from . import history  # noqa: F401
from . import inspection  # noqa: F401
from . import layer  # noqa: F401
from . import smart_object  # noqa: F401
from . import mask  # noqa: F401
from . import mockup  # noqa: F401
from . import selection  # noqa: F401
from . import shape  # noqa: F401
from . import text  # noqa: F401
from . import transform  # noqa: F401
