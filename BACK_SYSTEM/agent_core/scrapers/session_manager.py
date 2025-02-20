"""
Manejo de sesiones y anti-bloqueo para scrapers.
"""

import random
import asyncio
from typing import Dict, Optional, List
import logging
from datetime import datetime, timedelta


class SessionManager:
    """
    Gestiona sesiones para scraping, incluyendo:
    - Rotación de User Agents
    - Delays entre requests
    - Control de intentos
    """

    DEFAULT_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    ]

    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        max_retries: int = 3,
        user_agents: Optional[List[str]] = None,
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.user_agents = user_agents or self.DEFAULT_USER_AGENTS
        self.logger = logging.getLogger(__name__)
        self._last_request_time = datetime.now()
        self._current_user_agent = None
        self._retry_count = 0

    async def get_session_config(self) -> Dict:
        """
        Obtiene configuración para la próxima sesión.
        Incluye rotación de User Agent y cálculo de delay.
        """
        await self._enforce_delay()
        self._rotate_user_agent()

        return {
            "user_agent": self._current_user_agent,
            "headers": self._get_headers(),
            "retry_count": self._retry_count,
        }

    async def _enforce_delay(self):
        """
        Asegura un delay mínimo entre requests para evitar bloqueos.
        """
        now = datetime.now()
        time_since_last = (now - self._last_request_time).total_seconds()

        if time_since_last < self.min_delay:
            delay = random.uniform(
                self.min_delay - time_since_last, self.max_delay - time_since_last
            )
            await asyncio.sleep(delay)

        self._last_request_time = datetime.now()

    def _rotate_user_agent(self):
        """
        Rota el User Agent para simular diferentes navegadores.
        """
        if self._current_user_agent in self.user_agents:
            current_index = self.user_agents.index(self._current_user_agent)
            next_index = (current_index + 1) % len(self.user_agents)
            self._current_user_agent = self.user_agents[next_index]
        else:
            self._current_user_agent = random.choice(self.user_agents)

    def _get_headers(self) -> Dict:
        """
        Genera headers HTTP para simular un navegador real.
        """
        return {
            "User-Agent": self._current_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }

    async def handle_error(self, error: Exception) -> bool:
        """
        Maneja errores durante el scraping.
        Retorna True si se debe reintentar, False si se debe abortar.
        """
        self._retry_count += 1

        if self._retry_count > self.max_retries:
            self.logger.error(
                f"Máximo número de intentos alcanzado: {self.max_retries}"
            )
            return False

        delay = self._calculate_retry_delay()
        self.logger.warning(
            f"Error en intento {self._retry_count}/{self.max_retries}. "
            f"Esperando {delay} segundos antes de reintentar."
        )

        await asyncio.sleep(delay)
        return True

    def _calculate_retry_delay(self) -> float:
        """
        Calcula el delay para el próximo reintento usando backoff exponencial.
        """
        base_delay = 2**self._retry_count
        jitter = random.uniform(0, 0.5 * base_delay)
        return min(base_delay + jitter, 30)  # máximo 30 segundos

    def reset(self):
        """
        Reinicia el estado del session manager.
        """
        self._retry_count = 0
        self._last_request_time = datetime.now() - timedelta(seconds=self.max_delay)
