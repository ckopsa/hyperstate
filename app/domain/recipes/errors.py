from app.domain.errors import DomainError


class RecipeError(DomainError):
    """Base for domain-level recipe errors."""
    pass


class RecipeNotFound(DomainError):
    def __init__(self, recipe_id: str):
        self.recipe_id = recipe_id
        super().__init__(f"Recipe {recipe_id} not found")
