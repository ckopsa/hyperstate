from app.domain.errors import DomainError

class CurriculumNotFound(DomainError):
    def __init__(self, curriculum_id: str):
        self.curriculum_id = curriculum_id
        super().__init__(f"Curriculum {curriculum_id} not found.")

class CurriculumItemNotFound(DomainError):
    def __init__(self, item_id: str):
        self.item_id = item_id
        super().__init__(f"Curriculum item {item_id} not found.")
