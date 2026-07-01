"""Load the lab connection profile.

Order of precedence (highest first):
  1. Environment variables  VCF_<SECTION>_<KEY>   e.g. VCF_VCENTER_HOST
     (plus the shortcuts VCF_PASSWORD / VCF_USER applied to every section)
  2. config/lab.yaml         (git-ignored, copied from lab.example.yaml)
  3. config/lab.example.yaml (committed template / rtolab defaults)

This keeps endpoints, tokens and certs OUT of the source code — the migration
doc calls this out as a required practice (外部化 hard-coded endpoint/token/cert).
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _apply_env(cfg: dict) -> dict:
    """Overlay VCF_<SECTION>_<KEY> env vars, plus global VCF_USER / VCF_PASSWORD."""
    for section, values in cfg.items():
        if not isinstance(values, dict):
            env_key = f"VCF_{section.upper()}"
            if env_key in os.environ:
                cfg[section] = os.environ[env_key]
            continue
        for key in values:
            env_key = f"VCF_{section.upper()}_{key.upper()}"
            if env_key in os.environ:
                values[key] = os.environ[env_key]
        if "VCF_PASSWORD" in os.environ and "password" in values:
            values["password"] = os.environ["VCF_PASSWORD"]
        if "VCF_USER" in os.environ and "user" in values:
            values["user"] = os.environ["VCF_USER"]
    return cfg


def load(section: str | None = None) -> dict:
    """Return the full profile, or just one section (e.g. 'vcenter')."""
    example = _CONFIG_DIR / "lab.example.yaml"
    local = _CONFIG_DIR / "lab.yaml"

    cfg: dict = {}
    if example.exists():
        cfg = yaml.safe_load(example.read_text(encoding="utf-8")) or {}
    if local.exists():
        cfg = _deep_merge(cfg, yaml.safe_load(local.read_text(encoding="utf-8")) or {})
    cfg = _apply_env(cfg)

    if section is None:
        return cfg
    if section not in cfg:
        raise KeyError(f"section '{section}' not found in lab config")
    return cfg[section]


def verify_tls(cfg: dict | None = None):
    """Return the value to pass as requests' `verify=` (bool or CA bundle path)."""
    cfg = cfg or load()
    if cfg.get("ca_bundle"):
        return cfg["ca_bundle"]
    return bool(cfg.get("verify_tls", False))


if __name__ == "__main__":
    import json

    print(json.dumps(load(), indent=2, ensure_ascii=False))
