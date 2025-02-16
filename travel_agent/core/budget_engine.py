"""
Motor de presupuestos del agente de viajes.

Este módulo se encarga de:
1. Generar presupuestos
2. Gestionar versiones
3. Calcular costos
4. Aplicar personalizaciones
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
import uuid

from .schemas import TravelPackage, Budget, BudgetVersion, BudgetStatus, PaymentPlan
from ..memory.supabase import SupabaseMemory


class BudgetEngine:
    """Motor de presupuestos del agente de viajes."""

    def __init__(self):
        """Inicializar motor."""
        self.logger = logging.getLogger(__name__)
        self.memory = SupabaseMemory()

        # Configuración
        self.config = {
            "max_versions": 10,
            "validity_days": 7,
            "min_advance_payment": 0.3,  # 30%
            "installment_options": [3, 6, 12],
            "tax_rate": 0.21,  # 21% IVA
        }

    async def create_budget(
        self, packages: List[TravelPackage], metadata: Optional[Dict[str, Any]] = None
    ) -> Budget:
        """
        Crear nuevo presupuesto.

        Args:
            packages: Paquetes a incluir
            metadata: Metadatos adicionales

        Returns:
            Presupuesto generado
        """
        try:
            # Generar ID único
            budget_id = str(uuid.uuid4())

            # Calcular costos
            costs = await self._calculate_costs(packages)

            # Generar planes de pago
            payment_plans = self._generate_payment_plans(costs["total"])

            # Crear presupuesto
            budget = Budget(
                id=budget_id,
                created_at=datetime.now(),
                valid_until=self._calculate_validity(),
                packages=[p.dict() for p in packages],
                costs=costs,
                payment_plans=payment_plans,
                status=BudgetStatus.DRAFT,
                metadata=metadata or {},
                current_version=1,
                versions=[
                    BudgetVersion(
                        version=1,
                        timestamp=datetime.now(),
                        changes="Versión inicial",
                        content={
                            "packages": [p.dict() for p in packages],
                            "costs": costs,
                            "payment_plans": payment_plans,
                        },
                    )
                ],
            )

            # Almacenar presupuesto
            await self._store_budget(budget)

            return budget

        except Exception as e:
            self.logger.error(f"Error creando presupuesto: {str(e)}")
            raise

    async def update_budget(
        self,
        budget_id: str,
        packages: Optional[List[TravelPackage]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        changes: Optional[str] = None,
    ) -> Budget:
        """
        Actualizar presupuesto existente.

        Args:
            budget_id: ID del presupuesto
            packages: Nuevos paquetes
            metadata: Nuevos metadatos
            changes: Descripción de cambios

        Returns:
            Presupuesto actualizado
        """
        try:
            # Obtener presupuesto
            budget = await self.get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto no encontrado: {budget_id}")

            # Verificar versiones máximas
            if len(budget.versions) >= self.config["max_versions"]:
                raise ValueError(
                    f"Número máximo de versiones alcanzado: {self.config['max_versions']}"
                )

            # Actualizar paquetes si se proporcionan
            if packages:
                # Calcular nuevos costos
                costs = await self._calculate_costs(packages)

                # Generar nuevos planes de pago
                payment_plans = self._generate_payment_plans(costs["total"])

                # Crear nueva versión
                new_version = BudgetVersion(
                    version=budget.current_version + 1,
                    timestamp=datetime.now(),
                    changes=changes or "Actualización de paquetes",
                    content={
                        "packages": [p.dict() for p in packages],
                        "costs": costs,
                        "payment_plans": payment_plans,
                    },
                )

                # Actualizar presupuesto
                budget.packages = [p.dict() for p in packages]
                budget.costs = costs
                budget.payment_plans = payment_plans
                budget.current_version += 1
                budget.versions.append(new_version)

            # Actualizar metadatos si se proporcionan
            if metadata:
                budget.metadata.update(metadata)

            # Actualizar fecha de validez
            budget.valid_until = self._calculate_validity()

            # Almacenar cambios
            await self._store_budget(budget)

            return budget

        except Exception as e:
            self.logger.error(f"Error actualizando presupuesto: {str(e)}")
            raise

    async def get_budget(
        self, budget_id: str, version: Optional[int] = None
    ) -> Optional[Budget]:
        """
        Obtener presupuesto.

        Args:
            budget_id: ID del presupuesto
            version: Versión específica

        Returns:
            Presupuesto solicitado
        """
        try:
            # Obtener presupuesto
            budget_data = await self.memory.get_budget(budget_id)
            if not budget_data:
                return None

            budget = Budget(**budget_data)

            # Retornar versión específica si se solicita
            if version:
                version_data = next(
                    (v for v in budget.versions if v.version == version), None
                )
                if version_data:
                    budget.packages = version_data.content["packages"]
                    budget.costs = version_data.content["costs"]
                    budget.payment_plans = version_data.content["payment_plans"]
                    budget.current_version = version

            return budget

        except Exception as e:
            self.logger.error(f"Error obteniendo presupuesto: {str(e)}")
            return None

    async def approve_budget(
        self, budget_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Budget:
        """
        Aprobar presupuesto.

        Args:
            budget_id: ID del presupuesto
            metadata: Metadatos adicionales

        Returns:
            Presupuesto aprobado
        """
        try:
            budget = await self.get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto no encontrado: {budget_id}")

            # Actualizar estado
            budget.status = BudgetStatus.APPROVED
            budget.metadata.update(metadata or {})

            # Almacenar cambios
            await self._store_budget(budget)

            return budget

        except Exception as e:
            self.logger.error(f"Error aprobando presupuesto: {str(e)}")
            raise

    async def reject_budget(
        self, budget_id: str, reason: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Budget:
        """
        Rechazar presupuesto.

        Args:
            budget_id: ID del presupuesto
            reason: Razón del rechazo
            metadata: Metadatos adicionales

        Returns:
            Presupuesto rechazado
        """
        try:
            budget = await self.get_budget(budget_id)
            if not budget:
                raise ValueError(f"Presupuesto no encontrado: {budget_id}")

            # Actualizar estado
            budget.status = BudgetStatus.REJECTED
            budget.metadata.update(metadata or {}, rejection_reason=reason)

            # Almacenar cambios
            await self._store_budget(budget)

            return budget

        except Exception as e:
            self.logger.error(f"Error rechazando presupuesto: {str(e)}")
            raise

    async def _calculate_costs(self, packages: List[TravelPackage]) -> Dict[str, float]:
        """Calcular costos del presupuesto."""
        try:
            # Calcular subtotal
            subtotal = sum(package.price for package in packages)

            # Calcular impuestos
            taxes = subtotal * self.config["tax_rate"]

            # Calcular total
            total = subtotal + taxes

            return {"subtotal": subtotal, "taxes": taxes, "total": total}

        except Exception as e:
            self.logger.error(f"Error calculando costos: {str(e)}")
            raise

    def _generate_payment_plans(self, total: float) -> List[PaymentPlan]:
        """Generar planes de pago."""
        try:
            plans = []

            # Calcular pago anticipado mínimo
            advance_payment = total * self.config["min_advance_payment"]

            # Generar planes por cuotas
            for installments in self.config["installment_options"]:
                # Calcular monto restante
                remaining = total - advance_payment

                # Calcular cuota mensual
                monthly_payment = remaining / installments

                # Crear plan
                plan = PaymentPlan(
                    type=f"Plan {installments} cuotas",
                    advance_payment=advance_payment,
                    installments=installments,
                    monthly_payment=monthly_payment,
                    total_amount=total,
                )

                plans.append(plan)

            return plans

        except Exception as e:
            self.logger.error(f"Error generando planes de pago: {str(e)}")
            return []

    def _calculate_validity(self) -> datetime:
        """Calcular fecha de validez del presupuesto."""
        try:
            return datetime.now().replace(hour=23, minute=59, second=59) + timedelta(
                days=self.config["validity_days"]
            )

        except Exception as e:
            self.logger.error(f"Error calculando validez: {str(e)}")
            return datetime.now()

    async def _store_budget(self, budget: Budget):
        """Almacenar presupuesto en base de conocimiento."""
        try:
            await self.memory.store_budget(budget.dict())

        except Exception as e:
            self.logger.error(f"Error almacenando presupuesto: {str(e)}")
            raise
