"""
Browser Manager para extracción de datos usando browser-use.

Este módulo implementa un gestor avanzado de navegación web que:
1. Usa browser-use para automatización inteligente
2. Maneja extracción dinámica de datos
3. Procesa interacciones complejas
4. Gestiona caché eficientemente
5. Proporciona feedback detallado
"""

from typing import Dict, List, Optional, Union, Any, AsyncContextManager
import asyncio
import logging
from datetime import datetime
import json
from pathlib import Path
import hashlib
import os
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager

try:
    from browser_use import Agent, Browser, BrowserConfig, BrowserContextConfig
    from browser_use.browser.browser import BrowserContext
    from langchain_openai import ChatOpenAI
except ImportError as e:
    print(f"Error al importar módulos: {e}")
    raise ImportError(
        "browser-use no está instalado. Instálalo con: pip install browser-use"
    )

from ..core.config import config

class InteractionType(Enum):
    """Tipos de interacción soportados."""
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    WAIT = "wait"
    CUSTOM = "custom"

@dataclass
class ExtractionResult:
    """Resultado de extracción de datos."""
    success: bool
    data: Dict[str, Any]
    errors: List[str]
    timestamp: datetime = datetime.now()

class BrowserManager:
    """
    Gestor avanzado de navegación web.
    
    Características:
    1. Automatización inteligente con browser-use
    2. Extracción de datos estructurados
    3. Manejo de interacciones complejas
    4. Sistema de caché integrado
    5. Gestión de errores robusta
    """
    
    def __init__(
        self,
        llm_model: str = "gpt-4",
        cache_dir: Optional[str] = None,
        browser_config: Optional[Dict] = None
    ):
        """Inicializar Browser Manager."""
        self.logger = logging.getLogger(__name__)
        
        # Configurar LLM
        self.llm = ChatOpenAI(
            model=llm_model,
            api_key=config.OPENAI_API_KEY
        )
        
        # Configurar browser-use
        self.browser_config = BrowserConfig(
            headless=config.BROWSER_HEADLESS,
            slow_mo=config.BROWSER_SLOW_MO,
            timeout=config.BROWSER_TIMEOUT,
            **(browser_config or {})
        )
        
        # Configurar caché
        self.cache_dir = cache_dir or config.CACHE_DIR
        self.cache_ttl = config.CACHE_TTL
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Inicializar agent
        self.agent = Agent(
            llm=self.llm,
            browser_config=self.browser_config
        )
    
    @asynccontextmanager
    async def get_browser(self) -> AsyncContextManager[Browser]:
        """Obtener instancia de navegador."""
        try:
            browser = await self.agent.get_browser()
            yield browser
        finally:
            if browser:
                await browser.close()
    
    async def extract_data(
        self,
        url: str,
        extraction_template: Dict[str, Any],
        use_cache: bool = True
    ) -> ExtractionResult:
        """Extraer datos de una URL usando un template."""
        try:
            # Verificar caché
            if use_cache:
                cache_key = self._get_cache_key(url, extraction_template)
                cached_data = self._get_from_cache(cache_key)
                if cached_data:
                    return ExtractionResult(
                        success=True,
                        data=cached_data,
                        errors=[]
                    )
            
            # Extraer datos
            async with self.get_browser() as browser:
                # Navegar a la URL
                page = await browser.new_page()
                await page.goto(url)
                
                # Aplicar template de extracción
                result = await self.agent.run(
                    page=page,
                    task=extraction_template
                )
                
                # Procesar resultado
                if result.success:
                    # Guardar en caché
                    if use_cache:
                        self._save_to_cache(
                            cache_key,
                            result.data
                        )
                    
                    return ExtractionResult(
                        success=True,
                        data=result.data,
                        errors=[]
                    )
                else:
                    return ExtractionResult(
                        success=False,
                        data={},
                        errors=[str(result.error)]
                    )
                    
        except Exception as e:
            self.logger.error(f"Error extrayendo datos: {str(e)}")
            return ExtractionResult(
                success=False,
                data={},
                errors=[str(e)]
            )
    
    async def interact(
        self,
        page: Any,
        interaction_type: InteractionType,
        selector: str,
        value: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> bool:
        """Realizar una interacción en la página."""
        try:
            timeout = timeout or config.BROWSER_TIMEOUT
            
            if interaction_type == InteractionType.CLICK:
                await page.click(selector, timeout=timeout)
            elif interaction_type == InteractionType.TYPE:
                await page.type(selector, value or "", timeout=timeout)
            elif interaction_type == InteractionType.SELECT:
                await page.select(selector, value or "", timeout=timeout)
            elif interaction_type == InteractionType.SCROLL:
                await page.evaluate(f"document.querySelector('{selector}').scrollIntoView()")
            elif interaction_type == InteractionType.WAIT:
                await page.wait_for_selector(selector, timeout=timeout)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error en interacción {interaction_type}: {str(e)}")
            return False
    
    def _get_cache_key(self, url: str, template: Dict[str, Any]) -> str:
        """Generar clave de caché."""
        content = f"{url}:{json.dumps(template, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Obtener datos de caché."""
        cache_file = Path(self.cache_dir) / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
            
        # Verificar TTL
        if (
            datetime.now().timestamp() - cache_file.stat().st_mtime
            > self.cache_ttl
        ):
            cache_file.unlink()
            return None
            
        try:
            with open(cache_file) as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error leyendo caché: {str(e)}")
            return None
    
    def _save_to_cache(self, cache_key: str, data: Dict[str, Any]):
        """Guardar datos en caché."""
        try:
            cache_file = Path(self.cache_dir) / f"{cache_key}.json"
            with open(cache_file, "w") as f:
                json.dump(data, f)
