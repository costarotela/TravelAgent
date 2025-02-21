"""
Sistema de flujo de aprobación de presupuestos.

Este módulo implementa:
1. Estados del workflow de aprobación
2. Transiciones y validaciones
3. Roles y permisos
4. Registro de cambios y auditoría
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from prometheus_client import Counter, Histogram

from .validator import get_budget_validator, ValidationIssue, ValidationLevel
from .models import Budget
from ..vendors.preferences import get_preference_manager

# Métricas
APPROVAL_OPERATIONS = Counter(
    "budget_approval_operations_total",
    "Number of budget approval operations",
    ["operation_type", "result"],
)

APPROVAL_LATENCY = Histogram(
    "budget_approval_latency_seconds",
    "Latency of budget approval operations",
    ["operation_type"],
)


class ApprovalRole(Enum):
    """Roles en el proceso de aprobación."""

    SELLER = "seller"  # Vendedor que crea/modifica
    SUPERVISOR = "supervisor"  # Supervisor que revisa
    MANAGER = "manager"  # Gerente que aprueba final
    SYSTEM = "system"  # Sistema (validaciones automáticas)


class ApprovalState(Enum):
    """Estados del workflow de aprobación."""

    DRAFT = "draft"  # En construcción
    PENDING_REVIEW = "pending_review"  # Esperando revisión
    IN_REVIEW = "in_review"  # En revisión
    CHANGES_REQUESTED = "changes_requested"  # Cambios solicitados
    PENDING_APPROVAL = "pending_approval"  # Esperando aprobación final
    APPROVED = "approved"  # Aprobado
    REJECTED = "rejected"  # Rechazado
    CANCELLED = "cancelled"  # Cancelado


@dataclass
class ApprovalTransition:
    """Transición entre estados."""

    from_state: ApprovalState
    to_state: ApprovalState
    allowed_roles: Set[ApprovalRole]
    requires_comment: bool = False
    requires_validation: bool = True


@dataclass
class ApprovalComment:
    """Comentario en el proceso de aprobación."""

    comment_id: UUID = field(default_factory=uuid4)
    user_id: str
    role: ApprovalRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ApprovalHistory:
    """Historial de cambios de estado."""

    transition_id: UUID = field(default_factory=uuid4)
    from_state: ApprovalState
    to_state: ApprovalState
    user_id: str
    role: ApprovalRole
    timestamp: datetime = field(default_factory=datetime.now)
    comment: Optional[str] = None
    validation_issues: List[ValidationIssue] = field(default_factory=list)


class ApprovalWorkflow:
    """
    Workflow de aprobación de presupuestos.
    
    Gestiona:
    1. Estados y transiciones
    2. Roles y permisos
    3. Validaciones
    4. Historial y auditoría
    """

    def __init__(self):
        """Inicializar workflow."""
        self._setup_transitions()
        self.validator = get_budget_validator()
        self.preference_manager = get_preference_manager()

    def _setup_transitions(self):
        """Configurar transiciones permitidas."""
        self.transitions = {
            ApprovalState.DRAFT: [
                ApprovalTransition(
                    from_state=ApprovalState.DRAFT,
                    to_state=ApprovalState.PENDING_REVIEW,
                    allowed_roles={ApprovalRole.SELLER},
                    requires_validation=True,
                ),
                ApprovalTransition(
                    from_state=ApprovalState.DRAFT,
                    to_state=ApprovalState.CANCELLED,
                    allowed_roles={ApprovalRole.SELLER},
                    requires_comment=True,
                ),
            ],
            ApprovalState.PENDING_REVIEW: [
                ApprovalTransition(
                    from_state=ApprovalState.PENDING_REVIEW,
                    to_state=ApprovalState.IN_REVIEW,
                    allowed_roles={ApprovalRole.SUPERVISOR},
                ),
            ],
            ApprovalState.IN_REVIEW: [
                ApprovalTransition(
                    from_state=ApprovalState.IN_REVIEW,
                    to_state=ApprovalState.CHANGES_REQUESTED,
                    allowed_roles={ApprovalRole.SUPERVISOR},
                    requires_comment=True,
                ),
                ApprovalTransition(
                    from_state=ApprovalState.IN_REVIEW,
                    to_state=ApprovalState.PENDING_APPROVAL,
                    allowed_roles={ApprovalRole.SUPERVISOR},
                ),
            ],
            ApprovalState.CHANGES_REQUESTED: [
                ApprovalTransition(
                    from_state=ApprovalState.CHANGES_REQUESTED,
                    to_state=ApprovalState.DRAFT,
                    allowed_roles={ApprovalRole.SELLER},
                ),
            ],
            ApprovalState.PENDING_APPROVAL: [
                ApprovalTransition(
                    from_state=ApprovalState.PENDING_APPROVAL,
                    to_state=ApprovalState.APPROVED,
                    allowed_roles={ApprovalRole.MANAGER},
                    requires_validation=True,
                ),
                ApprovalTransition(
                    from_state=ApprovalState.PENDING_APPROVAL,
                    to_state=ApprovalState.REJECTED,
                    allowed_roles={ApprovalRole.MANAGER},
                    requires_comment=True,
                ),
            ],
        }

    def can_transition(
        self,
        from_state: ApprovalState,
        to_state: ApprovalState,
        role: ApprovalRole,
    ) -> bool:
        """
        Verificar si una transición es permitida.
        
        Args:
            from_state: Estado actual
            to_state: Estado destino
            role: Rol que intenta la transición
            
        Returns:
            True si la transición es permitida
        """
        if from_state not in self.transitions:
            return False
            
        for transition in self.transitions[from_state]:
            if (
                transition.to_state == to_state
                and role in transition.allowed_roles
            ):
                return True
                
        return False

    def get_required_validation(
        self,
        from_state: ApprovalState,
        to_state: ApprovalState,
    ) -> bool:
        """
        Verificar si la transición requiere validación.
        
        Args:
            from_state: Estado actual
            to_state: Estado destino
            
        Returns:
            True si se requiere validación
        """
        if from_state not in self.transitions:
            return False
            
        for transition in self.transitions[from_state]:
            if transition.to_state == to_state:
                return transition.requires_validation
                
        return False

    def get_required_comment(
        self,
        from_state: ApprovalState,
        to_state: ApprovalState,
    ) -> bool:
        """
        Verificar si la transición requiere comentario.
        
        Args:
            from_state: Estado actual
            to_state: Estado destino
            
        Returns:
            True si se requiere comentario
        """
        if from_state not in self.transitions:
            return False
            
        for transition in self.transitions[from_state]:
            if transition.to_state == to_state:
                return transition.requires_comment
                
        return False

    def validate_transition(
        self,
        budget: Budget,
        from_state: ApprovalState,
        to_state: ApprovalState,
        role: ApprovalRole,
        user_id: str,
        comment: Optional[str] = None,
    ) -> List[ValidationIssue]:
        """
        Validar una transición de estado.
        
        Args:
            budget: Presupuesto a validar
            from_state: Estado actual
            to_state: Estado destino
            role: Rol que intenta la transición
            user_id: ID del usuario
            comment: Comentario opcional
            
        Returns:
            Lista de problemas encontrados
        """
        issues = []
        
        # Verificar permiso de transición
        if not self.can_transition(from_state, to_state, role):
            issues.append(
                ValidationIssue(
                    rule=None,
                    message=(
                        f"Transición no permitida de {from_state.value} "
                        f"a {to_state.value} para rol {role.value}"
                    ),
                    context={
                        "from_state": from_state.value,
                        "to_state": to_state.value,
                        "role": role.value,
                    },
                )
            )
            return issues
            
        # Verificar comentario requerido
        if (
            self.get_required_comment(from_state, to_state)
            and not comment
        ):
            issues.append(
                ValidationIssue(
                    rule=None,
                    message="Se requiere comentario para esta transición",
                    context={
                        "from_state": from_state.value,
                        "to_state": to_state.value,
                    },
                )
            )
            
        # Realizar validaciones si es requerido
        if self.get_required_validation(from_state, to_state):
            validation_issues = self.validator.validate_budget(
                budget, user_id
            )
            issues.extend(validation_issues)
            
        return issues

    def transition_state(
        self,
        budget: Budget,
        from_state: ApprovalState,
        to_state: ApprovalState,
        role: ApprovalRole,
        user_id: str,
        comment: Optional[str] = None,
    ) -> List[ValidationIssue]:
        """
        Realizar transición de estado.
        
        Args:
            budget: Presupuesto a transicionar
            from_state: Estado actual
            to_state: Estado destino
            role: Rol que realiza la transición
            user_id: ID del usuario
            comment: Comentario opcional
            
        Returns:
            Lista de problemas encontrados
        """
        with APPROVAL_LATENCY.labels("transition").time():
            # Validar transición
            issues = self.validate_transition(
                budget, from_state, to_state, role, user_id, comment
            )
            
            if not issues or all(
                issue.rule and issue.rule.level != ValidationLevel.ERROR
                for issue in issues
            ):
                # Registrar historial
                history = ApprovalHistory(
                    from_state=from_state,
                    to_state=to_state,
                    user_id=user_id,
                    role=role,
                    comment=comment,
                    validation_issues=issues,
                )
                
                # Registrar métricas
                APPROVAL_OPERATIONS.labels(
                    operation_type="transition",
                    result="success",
                ).inc()
                
                return []
            else:
                # Registrar métricas
                APPROVAL_OPERATIONS.labels(
                    operation_type="transition",
                    result="error",
                ).inc()
                
                return issues


# Instancia global
approval_workflow = ApprovalWorkflow()


def get_approval_workflow() -> ApprovalWorkflow:
    """
    Obtener instancia del workflow.
    
    Returns:
        Instancia única del workflow
    """
    return approval_workflow
