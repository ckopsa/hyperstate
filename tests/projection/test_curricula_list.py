import pytest

from app.domain.curricula.aggregate import Curriculum
from app.hyperstate.response import ActorContext
from app.projection.curricula.list import CurriculumListProjection

@pytest.fixture
def actor():
    return ActorContext(id="parent-1", roles=["parent"])

@pytest.fixture
def curricula():
    return [
        Curriculum(id="CUR-1", name="Math Curriculum", grade_level="1st", description="First grade math"),
        Curriculum(id="CUR-2", name="Science Curriculum", grade_level="2nd"),
    ]

class TestCurriculumListProjection:
    def test_build_list_projection(self, curricula, actor):
        projection = CurriculumListProjection(curricula=curricula, actor=actor)
        response = projection.build()
        
        # Title and self
        assert response.title == "Curricula"
        assert response.self_ == "/curricula"
        
        # View context
        assert response.context.domain == "curricula"
        assert response.context.aggregate == "curricula"
        assert response.context.state == "collection"
        
        # Nav links
        assert len(response.nav) == 1
        assert response.nav[0].label == "Dashboard"
        assert response.nav[0].href == "/dashboard"
        assert response.nav[0].rel == "parent"
        
        # Sections
        assert len(response.sections) == 2
        
        # Action section
        action_section = next(s for s in response.sections if s.kind == "action")
        assert action_section.key == "create-curriculum"
        assert action_section.method == "POST"
        assert action_section.href == "/curricula"
        
        # Action fields
        field_names = [f.name for f in action_section.fields]
        assert "name" in field_names
        assert "description" in field_names
        assert "grade_level" in field_names
        
        # List section
        list_section = next(s for s in response.sections if s.kind == "list")
        assert list_section.title == "All Curricula"
        assert len(list_section.items) == 2
        
        # List items data
        assert list_section.items[0].href == "/curricula/CUR-1"
        assert list_section.items[0].data["name"] == "Math Curriculum"
        assert list_section.items[0].data["grade"] == "1st"
        assert list_section.items[0].data["description"] == "First grade math"

        assert list_section.items[1].href == "/curricula/CUR-2"
        assert list_section.items[1].data["name"] == "Science Curriculum"
        assert list_section.items[1].data["grade"] == "2nd"
        assert list_section.items[1].data["description"] == "-"
