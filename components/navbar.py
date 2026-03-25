import dash_bootstrap_components as dbc
from dash import html

navbar = dbc.Navbar(
    dbc.Container([
        dbc.Row([
            dbc.Col(html.A(
                dbc.NavbarBrand("ML Competitor Intelligence"),
                href="/", className="text-decoration-none",
            ), width="auto"),
            dbc.Col(dbc.Nav([
                dbc.NavItem(dbc.NavLink("Busca", href="/search")),
                dbc.NavItem(dbc.NavLink("Concorrentes", href="/competitors")),
                dbc.NavItem(dbc.NavLink("Insights IA", href="/insights")),
                dbc.NavItem(dbc.NavLink("Exportar", href="/export")),
                dbc.NavItem(dbc.NavLink("Settings", href="/settings")),
            ], navbar=True)),
        ], align="center", className="g-0 w-100"),
    ], fluid=True),
    color="dark", dark=True, className="mb-4",
)
