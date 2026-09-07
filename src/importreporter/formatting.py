"""
formatting.py
=============
Petites fonctions de formatage réutilisées dans le rapport, équivalentes à :
- `format(x, big.mark = " ")` (R)             -> `format_number`
- `scales::percent(x, accuracy = 0.1)` (R)    -> `format_percent`
- transliteration + nettoyage de nom de fichier (stringi + gsub, R)
                                                -> `sanitize_filename`
"""

from __future__ import annotations

import re
import unicodedata
from numbers import Number

from unidecode import unidecode


def format_number(value: Number | None, decimals: int = 0) -> str:
    """Formate un nombre avec des espaces comme séparateur de milliers.

    Équivalent de `format(x, big.mark = " ", scientific = FALSE)` en R.
    """
    if value is None:
        return "0"
    try:
        if decimals == 0:
            return f"{float(value):,.0f}".replace(",", "\u00a0")
        return f"{float(value):,.{decimals}f}".replace(",", "\u00a0")
    except (TypeError, ValueError):
        return str(value)


def format_percent(value: Number | None, decimals: int = 1) -> str:
    """Équivalent de `scales::percent(x, accuracy = 0.1)`."""
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.{decimals}f}\u00a0%"
    except (TypeError, ValueError):
        return str(value)


def sanitize_filename(name: str) -> str:
    """Nettoie un nom de source pour en faire un nom de fichier sûr.
    """
    ascii_name = unidecode(name)
    ascii_name = unicodedata.normalize("NFKD", ascii_name)
    ascii_name = ascii_name.replace(" ", "_")
    ascii_name = re.sub(r"[^A-Za-z0-9_]", "", ascii_name)
    return ascii_name or "rapport_sans_nom"


def csv_download_link(df, filename: str, label: str) -> str:
    """Génère un lien HTML de téléchargement d'un DataFrame en CSV encodé en
    base64 — équivalent du bloc `base64enc::base64encode()` du rapport.Rmd.
    """
    import base64

    if df is None or df.empty:
        return ""
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    b64 = base64.b64encode(csv_bytes).decode("ascii")
    return (
        f'<a download="{filename}" '
        f'href="data:text/csv;base64,{b64}" class="btn-download">{label}</a>'
    )


def parse_id_list(list_import_raw: str) -> list[str]:
    """Transforme la chaîne `list_import` (ex: "'7087_390','7087_391'") issue
    de la vue SQL en une vraie liste Python de chaînes, pour l'utiliser avec
    un bind parameter `expanding=True`.
    """
    # Retire les guillemets simples éventuels puis découpe sur la virgule
    cleaned = list_import_raw.replace("'", "").replace('"', "")
    return [item.strip() for item in cleaned.split(",") if item.strip()]
