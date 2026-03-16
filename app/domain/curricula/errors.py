class CurriculumNotFound(Exception):
    def __init__(self, curriculum_id: str):
        self.curriculum_id = curriculum_id
        super().__init__(f"Curriculum {curriculum_id} not found")

class CurriculumError(Exception):
    pass
