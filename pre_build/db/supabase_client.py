"""Supabase client factory for VAYU.

Reads credentials from environment variables (loaded from a local ``.env``
file via python-dotenv when present). Two clients are exposed:

  • get_supabase()          -> uses the anon key  (respects Row Level Security)
  • get_service_supabase()  -> uses the service_role key (bypasses RLS;
                               server-side only — seeding, writes, migrations)

Both are cached so the whole process shares one connection per key.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client, Client

# Load .env from the project root if it exists (no-op in production envs
# where the variables are already set).
load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            f"Copy .env.example to .env and fill in your Supabase credentials."
        )
    return value


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Anon client — subject to RLS. Safe for read-mostly app access."""
    return create_client(_require("SUPABASE_URL"), _require("SUPABASE_ANON_KEY"))


@lru_cache(maxsize=1)
def get_service_supabase() -> Client:
    """Service-role client — bypasses RLS. Use only on the server."""
    return create_client(
        _require("SUPABASE_URL"), _require("SUPABASE_SERVICE_ROLE_KEY")
    )
