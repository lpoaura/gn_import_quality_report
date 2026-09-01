"""
tables.py
=========
Mise en forme HTML des tableaux du rapport.

R (kableExtra)                              Python
kable(...) %>% kable_styling(...)       ->  render_static_table()   (tableau simple, propre)
DT::datatable(...)                      ->  render_interactive_table()  (recherche/tri/pagination JS)

Les tableaux "interactifs" nécessitent la librairie DataTables.js, chargée
une seule fois dans le `<head>` du template (jQuery + DataTables CDN).
"""

from __future__ import annotations

import itertools

import pandas as pd

_table_id_counter = itertools.count(1)


def _next_table_id(prefix: str) -> str:
    return f"{prefix}_{next(_table_id_counter)}"


def render_static_table(df: pd.DataFrame, table_id: str | None = None) -> str:
    """Tableau HTML simple et propre, sans JS — équivalent `kable_styling()`."""
    if df.empty:
        return "<p class='table-empty'>Aucune donnée disponible.</p>"
    table_id = table_id or _next_table_id("tbl")
    return df.to_html(
        index=False,
        classes="report-table",
        border=0,
        escape=True,
        table_id=table_id,
        na_rep="-",
    )


def render_interactive_table(df: pd.DataFrame, table_id: str | None = None, page_length: int = 10) -> str:
    """Tableau HTML avec recherche/tri/pagination via DataTables.js —
    équivalent `DT::datatable()`."""
    if df.empty:
        return "<p class='table-empty'>Aucune donnée disponible.</p>"
    table_id = table_id or _next_table_id("dt")
    html = df.to_html(
        index=False,
        classes="report-table display",
        border=0,
        escape=True,
        table_id=table_id,
        na_rep="-",
    )
    script = f"""
    <script>
      $(function() {{
        $('#{table_id}').DataTable({{
          pageLength: {page_length},
          language: {{
            url: 'https://cdn.datatables.net/plug-ins/1.13.8/i18n/fr-FR.json'
          }}
        }});
      }});
    </script>
    """
    return html + script
