"""
Motor de visualización del agente de viajes.

Este módulo se encarga de:
1. Generar visualizaciones
2. Crear reportes
3. Exportar datos
4. Formatear resultados
"""

from typing import Dict, Any, Optional, List, Union
import logging
from datetime import datetime
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from .schemas import (
    TravelPackage,
    SearchCriteria,
    Provider,
    Booking,
    Budget,
    MarketTrend,
    VisualizationType,
)
from ..memory.supabase import SupabaseMemory


class VisualizationEngine:
    """Motor de visualización del agente de viajes."""

    def __init__(self):
        """Inicializar motor."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

        # Configuración
        self.config = {
            "output_dir": "visualizations",
            "max_items": 100,
            "default_format": "png",
            "dpi": 300,
        }

        # Configuración de estilos
        plt.style.use("seaborn")
        sns.set_palette("husl")

    async def start(self):
        """Iniciar motor."""
        try:
            # Crear directorio de salida
            os.makedirs(self.config["output_dir"], exist_ok=True)

            self.logger.info("Motor de visualización iniciado")

        except Exception as e:
            self.logger.error(f"Error iniciando motor: {str(e)}")
            raise

    async def create_visualization(
        self,
        data: Union[List[Any], pd.DataFrame],
        viz_type: VisualizationType,
        title: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Crear visualización.

        Args:
            data: Datos a visualizar
            viz_type: Tipo de visualización
            title: Título
            metadata: Metadatos adicionales

        Returns:
            Ruta al archivo generado
        """
        try:
            # Convertir a DataFrame si es necesario
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data

            # Crear figura
            plt.figure(figsize=(12, 8))

            # Generar visualización
            if viz_type == VisualizationType.LINE:
                await self._create_line_plot(df, title, metadata)
            elif viz_type == VisualizationType.BAR:
                await self._create_bar_plot(df, title, metadata)
            elif viz_type == VisualizationType.SCATTER:
                await self._create_scatter_plot(df, title, metadata)
            elif viz_type == VisualizationType.PIE:
                await self._create_pie_plot(df, title, metadata)
            elif viz_type == VisualizationType.HEATMAP:
                await self._create_heatmap(df, title, metadata)
            else:
                raise ValueError(f"Tipo de visualización no válido: {viz_type}")

            # Guardar figura
            output_path = self._get_output_path(title)
            plt.savefig(output_path, dpi=self.config["dpi"], bbox_inches="tight")
            plt.close()

            return output_path

        except Exception as e:
            self.logger.error(f"Error creando visualización: {str(e)}")
            raise

    async def create_price_trend(
        self, packages: List[TravelPackage], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crear visualización de tendencia de precios.

        Args:
            packages: Lista de paquetes
            metadata: Metadatos adicionales

        Returns:
            Ruta al archivo generado
        """
        try:
            # Preparar datos
            data = []
            for package in packages:
                data.append(
                    {
                        "date": package.date,
                        "price": package.price,
                        "provider": package.provider_id,
                        "destination": package.destination,
                    }
                )

            df = pd.DataFrame(data)

            # Crear visualización
            return await self.create_visualization(
                data=df,
                viz_type=VisualizationType.LINE,
                title="Tendencia de Precios",
                metadata={
                    "x": "date",
                    "y": "price",
                    "hue": "provider",
                    **(metadata or {}),
                },
            )

        except Exception as e:
            self.logger.error(f"Error creando tendencia de precios: {str(e)}")
            raise

    async def create_demand_analysis(
        self, packages: List[TravelPackage], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crear visualización de análisis de demanda.

        Args:
            packages: Lista de paquetes
            metadata: Metadatos adicionales

        Returns:
            Ruta al archivo generado
        """
        try:
            # Preparar datos
            data = []
            for package in packages:
                data.append(
                    {
                        "destination": package.destination,
                        "views": package.stats.get("views", 0),
                        "bookings": package.stats.get("bookings", 0),
                        "conversion": package.stats.get("conversion_rate", 0),
                    }
                )

            df = pd.DataFrame(data)

            # Crear visualización
            return await self.create_visualization(
                data=df,
                viz_type=VisualizationType.BAR,
                title="Análisis de Demanda",
                metadata={
                    "x": "destination",
                    "y": "views",
                    "hue": "bookings",
                    **(metadata or {}),
                },
            )

        except Exception as e:
            self.logger.error(f"Error creando análisis de demanda: {str(e)}")
            raise

    async def create_market_summary(
        self, trends: List[MarketTrend], metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Crear visualización de resumen de mercado.

        Args:
            trends: Lista de tendencias
            metadata: Metadatos adicionales

        Returns:
            Ruta al archivo generado
        """
        try:
            # Preparar datos
            data = []
            for trend in trends:
                data.append(
                    {
                        "destination": trend.destination,
                        "price_trend": trend.price_trend,
                        "demand_trend": trend.demand_trend,
                        "confidence": trend.confidence,
                    }
                )

            df = pd.DataFrame(data)

            # Crear visualización
            return await self.create_visualization(
                data=df,
                viz_type=VisualizationType.HEATMAP,
                title="Resumen de Mercado",
                metadata={
                    "x": "destination",
                    "y": "price_trend",
                    "value": "confidence",
                    **(metadata or {}),
                },
            )

        except Exception as e:
            self.logger.error(f"Error creando resumen de mercado: {str(e)}")
            raise

    async def export_data(
        self, data: Any, format: str = "json", metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Exportar datos.

        Args:
            data: Datos a exportar
            format: Formato de exportación
            metadata: Metadatos adicionales

        Returns:
            Ruta al archivo generado
        """
        try:
            # Preparar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.{format}"
            output_path = os.path.join(self.config["output_dir"], filename)

            # Exportar según formato
            if format == "json":
                with open(output_path, "w") as f:
                    json.dump(data, f, indent=2)

            elif format == "csv":
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([data])
                df.to_csv(output_path, index=False)

            elif format == "excel":
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([data])
                df.to_excel(output_path, index=False)

            else:
                raise ValueError(f"Formato no válido: {format}")

            return output_path

        except Exception as e:
            self.logger.error(f"Error exportando datos: {str(e)}")
            raise

    async def _create_line_plot(
        self, df: pd.DataFrame, title: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Crear gráfico de líneas."""
        try:
            metadata = metadata or {}

            sns.lineplot(
                data=df,
                x=metadata.get("x", df.columns[0]),
                y=metadata.get("y", df.columns[1]),
                hue=metadata.get("hue"),
            )

            plt.title(title)
            plt.xticks(rotation=45)

        except Exception as e:
            self.logger.error(f"Error creando line plot: {str(e)}")
            raise

    async def _create_bar_plot(
        self, df: pd.DataFrame, title: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Crear gráfico de barras."""
        try:
            metadata = metadata or {}

            sns.barplot(
                data=df,
                x=metadata.get("x", df.columns[0]),
                y=metadata.get("y", df.columns[1]),
                hue=metadata.get("hue"),
            )

            plt.title(title)
            plt.xticks(rotation=45)

        except Exception as e:
            self.logger.error(f"Error creando bar plot: {str(e)}")
            raise

    async def _create_scatter_plot(
        self, df: pd.DataFrame, title: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Crear gráfico de dispersión."""
        try:
            metadata = metadata or {}

            sns.scatterplot(
                data=df,
                x=metadata.get("x", df.columns[0]),
                y=metadata.get("y", df.columns[1]),
                hue=metadata.get("hue"),
                size=metadata.get("size"),
            )

            plt.title(title)

        except Exception as e:
            self.logger.error(f"Error creando scatter plot: {str(e)}")
            raise

    async def _create_pie_plot(
        self, df: pd.DataFrame, title: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Crear gráfico circular."""
        try:
            metadata = metadata or {}

            plt.pie(
                df[metadata.get("values", df.columns[1])],
                labels=df[metadata.get("labels", df.columns[0])],
                autopct="%1.1f%%",
            )

            plt.title(title)

        except Exception as e:
            self.logger.error(f"Error creando pie plot: {str(e)}")
            raise

    async def _create_heatmap(
        self, df: pd.DataFrame, title: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Crear mapa de calor."""
        try:
            metadata = metadata or {}

            pivot_table = pd.pivot_table(
                df,
                values=metadata.get("value", df.columns[2]),
                index=metadata.get("y", df.columns[1]),
                columns=metadata.get("x", df.columns[0]),
            )

            sns.heatmap(pivot_table, annot=True, cmap="YlOrRd", fmt=".2f")

            plt.title(title)

        except Exception as e:
            self.logger.error(f"Error creando heatmap: {str(e)}")
            raise

    def _get_output_path(self, title: str) -> str:
        """Obtener ruta de salida para visualización."""
        try:
            # Limpiar título para nombre de archivo
            filename = "".join(c if c.isalnum() else "_" for c in title.lower())

            # Agregar timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}.{self.config['default_format']}"

            return os.path.join(self.config["output_dir"], filename)

        except Exception as e:
            self.logger.error(f"Error generando ruta: {str(e)}")
            raise
