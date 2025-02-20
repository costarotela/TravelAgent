"""Pages initialization."""

from .home import render_home_page
from .search import render_search_page
from .budgets import render_budget_page

__all__ = ["render_home_page", "render_search_page", "render_budget_page"]
