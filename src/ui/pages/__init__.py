"""Pages initialization."""
from src.ui.pages.budget_page import show as show_budget
from src.ui.pages.dashboard_page import show as show_dashboard
from src.ui.pages.providers_page import show as show_providers
from src.ui.pages.search_page import show as show_search

# Re-export the show functions
class budget_page:
    show = show_budget

class dashboard_page:
    show = show_dashboard

class providers_page:
    show = show_providers

class search_page:
    show = show_search

__all__ = [
    'budget_page',
    'dashboard_page',
    'providers_page',
    'search_page'
]
