"""Tests para el sistema de aprobación de presupuestos."""

import pytest
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from smart_travel_agency.core.budget.approval import (
    ApprovalRole,
    ApprovalState,
    get_approval_workflow,
)
from smart_travel_agency.core.budget.models import Budget, BudgetItem
from smart_travel_agency.core.vendors.preferences import (
    VendorPreferences,
    BasePreferences,
    BusinessPreferences,
    get_preference_manager,
)


@pytest.fixture
def sample_budget():
    """Fixture que crea un presupuesto de ejemplo."""
    return Budget(
        items=[
            BudgetItem(
                item_id=UUID("12345678-1234-5678-1234-567812345678"),
                provider_id="test_provider",
                description="Test Flight",
                price=Decimal("500.00"),
                currency="USD",
                quantity=1,
                type="flight",
            ),
            BudgetItem(
                item_id=UUID("22345678-1234-5678-1234-567812345678"),
                provider_id="test_provider",
                description="Test Hotel",
                price=Decimal("700.00"),
                currency="USD",
                quantity=1,
                type="accommodation",
            ),
        ],
        currency="USD",
    )


@pytest.fixture
def sample_preferences():
    """Fixture que crea preferencias de ejemplo."""
    base_prefs = BasePreferences(
        preferred_airlines=["TestAir"],
        min_rating=4.0,
        max_price=Decimal("2000.00"),
        excluded_providers=["bad_provider"],
    )

    business_prefs = BusinessPreferences(
        default_margin=Decimal("0.15"),
        min_margin=Decimal("0.05"),
        max_margin=Decimal("0.35"),
    )

    return VendorPreferences(
        vendor_id="test_vendor",
        name="Test Vendor",
        base=base_prefs,
        business_preferences=business_prefs,
    )


def test_workflow_initialization():
    """Test de inicialización del workflow."""
    workflow = get_approval_workflow()
    assert workflow is not None


def test_valid_transition_draft_to_review(sample_budget):
    """Test de transición válida de DRAFT a PENDING_REVIEW."""
    workflow = get_approval_workflow()
    
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.DRAFT,
        to_state=ApprovalState.PENDING_REVIEW,
        role=ApprovalRole.SELLER,
        user_id="test_seller",
    )
    
    assert not issues


def test_invalid_role_transition(sample_budget):
    """Test de transición con rol inválido."""
    workflow = get_approval_workflow()
    
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.DRAFT,
        to_state=ApprovalState.PENDING_REVIEW,
        role=ApprovalRole.MANAGER,  # Rol incorrecto
        user_id="test_manager",
    )
    
    assert len(issues) == 1
    assert "Transición no permitida" in issues[0].message


def test_missing_required_comment(sample_budget):
    """Test de transición que requiere comentario."""
    workflow = get_approval_workflow()
    
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.IN_REVIEW,
        to_state=ApprovalState.CHANGES_REQUESTED,
        role=ApprovalRole.SUPERVISOR,
        user_id="test_supervisor",
        # Sin comentario
    )
    
    assert len(issues) == 1
    assert "Se requiere comentario" in issues[0].message


def test_validation_on_transition(sample_budget):
    """Test de validación durante transición."""
    workflow = get_approval_workflow()
    
    # Agregar item con precio negativo
    sample_budget.items.append(
        BudgetItem(
            item_id=UUID("32345678-1234-5678-1234-567812345678"),
            provider_id="test_provider",
            description="Invalid Item",
            price=Decimal("-100.00"),
            currency="USD",
            quantity=1,
            type="activity",
        )
    )
    
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.DRAFT,
        to_state=ApprovalState.PENDING_REVIEW,
        role=ApprovalRole.SELLER,
        user_id="test_seller",
    )
    
    assert len(issues) > 0
    assert any("Monto inválido" in issue.message for issue in issues)


def test_full_approval_flow(sample_budget):
    """Test del flujo completo de aprobación."""
    workflow = get_approval_workflow()
    
    # DRAFT -> PENDING_REVIEW
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.DRAFT,
        to_state=ApprovalState.PENDING_REVIEW,
        role=ApprovalRole.SELLER,
        user_id="test_seller",
    )
    assert not issues
    
    # PENDING_REVIEW -> IN_REVIEW
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.PENDING_REVIEW,
        to_state=ApprovalState.IN_REVIEW,
        role=ApprovalRole.SUPERVISOR,
        user_id="test_supervisor",
    )
    assert not issues
    
    # IN_REVIEW -> PENDING_APPROVAL
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.IN_REVIEW,
        to_state=ApprovalState.PENDING_APPROVAL,
        role=ApprovalRole.SUPERVISOR,
        user_id="test_supervisor",
    )
    assert not issues
    
    # PENDING_APPROVAL -> APPROVED
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.PENDING_APPROVAL,
        to_state=ApprovalState.APPROVED,
        role=ApprovalRole.MANAGER,
        user_id="test_manager",
    )
    assert not issues


def test_rejection_flow(sample_budget):
    """Test del flujo de rechazo."""
    workflow = get_approval_workflow()
    
    # DRAFT -> PENDING_REVIEW
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.DRAFT,
        to_state=ApprovalState.PENDING_REVIEW,
        role=ApprovalRole.SELLER,
        user_id="test_seller",
    )
    assert not issues
    
    # PENDING_REVIEW -> IN_REVIEW
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.PENDING_REVIEW,
        to_state=ApprovalState.IN_REVIEW,
        role=ApprovalRole.SUPERVISOR,
        user_id="test_supervisor",
    )
    assert not issues
    
    # IN_REVIEW -> CHANGES_REQUESTED
    issues = workflow.transition_state(
        budget=sample_budget,
        from_state=ApprovalState.IN_REVIEW,
        to_state=ApprovalState.CHANGES_REQUESTED,
        role=ApprovalRole.SUPERVISOR,
        user_id="test_supervisor",
        comment="Se requieren ajustes en los precios",
    )
    assert not issues
