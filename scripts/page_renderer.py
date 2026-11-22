"""Render Pagefind entries and downloadable daily reports from the dashboard templates."""
import ctypes
from functools import lru_cache
import hashlib
import html
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "scripts/templates"
NATIVE = ROOT / "scripts/native"
_FIELDS = re.compile(r"@(TITLE_ATTR|REDIRECT_HASH|META_TAGS|BODY)@")


class _Field(ctypes.Structure):
    _fields_ = [("data", ctypes.c_char_p), ("size", ctypes.c_size_t)]


@lru_cache(maxsize=1)
def _library():
    policy = os.environ.get("DASHBOARD_PAGE_ENGINE", "auto")
    if policy not in {"auto", "native", "python"}:
        raise ValueError("unknown dashboard page engine")
    if policy == "python":
        return None
    filename = ("page_renderer_native.dll" if os.name == "nt" else
                "libpage_renderer_native.dylib" if sys.platform == "darwin" else "libpage_renderer_native.so")
    path = ROOT / ".local/native/bin" / filename
    if policy == "auto" and not path.is_file():
        return None
    sources = (NATIVE / "page_renderer.cpp", NATIVE / "page_renderer.hpp", NATIVE / "compiled_pages.hpp.in",
               TEMPLATES / "pagefind.html", TEMPLATES / "daily-download.html")
    identity = hashlib.sha256("".join(hashlib.sha256(p.read_bytes()).hexdigest() for p in sources).encode()).hexdigest()
    lib = ctypes.CDLL(str(path.resolve(strict=True)))
    lib.dashboard_page_identity.restype = ctypes.c_char_p
    if lib.dashboard_page_identity() != identity.encode():
        raise ValueError("dashboard page renderer requires a rebuild")
    lib.dashboard_render_page.argtypes = (ctypes.c_int, ctypes.POINTER(_Field), ctypes.c_size_t,
                                          ctypes.POINTER(ctypes.c_size_t))
    lib.dashboard_render_page.restype = ctypes.c_void_p
    return lib


@lru_cache(maxsize=2)
def _template(daily):
    return (TEMPLATES / ("daily-download.html" if daily else "pagefind.html")).read_text(encoding="utf-8")


def render_page(kind, title, body, redirect="", metadata=None):
    daily = kind == "daily"
    if not daily and kind != "index":
        raise ValueError("unknown dashboard page kind")
    pairs = [(str(k), str(v)) for k, v in (metadata or {}).items() if v]
    library = _library()
    if library is not None:
        values = [s.encode("utf-8") for s in (title, body, redirect, *(s for pair in pairs for s in pair))]
        fields = (_Field * len(values))(*(_Field(v, len(v)) for v in values))
        size = ctypes.c_size_t()
        result = library.dashboard_render_page(daily, fields, len(fields), ctypes.byref(size))
        if not result:
            raise RuntimeError("dashboard page rendering failed")
        return ctypes.string_at(result, size.value).decode("utf-8")
    if daily:
        for prefix in ('src="', "src='", 'href="', "href='"):
            body = body.replace(prefix+"assets/", prefix+"../../assets/")
    tags = "\n  ".join(f'<span hidden data-pagefind-meta="{html.escape(key+":"+value,quote=True)}"></span>'
                       for key, value in pairs)
    fields = dict(TITLE_ATTR=html.escape(title, quote=True), BODY=body, REDIRECT_HASH=redirect, META_TAGS=tags)
    return _FIELDS.sub(lambda match: fields[match[1]], _template(daily))
