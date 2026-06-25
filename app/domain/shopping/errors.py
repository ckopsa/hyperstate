from app.domain.errors import DomainError


class ShoppingError(DomainError):
    """Base for domain-level shopping errors."""
    pass


class ShoppingListNotFound(DomainError):
    def __init__(self, week_plan_id: str):
        self.week_plan_id = week_plan_id
        super().__init__(f"Shopping list for week plan {week_plan_id} not found")
