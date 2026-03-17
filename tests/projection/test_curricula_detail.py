import pytest

from app.domain.curricula.aggregate import Curriculum
from app.domain.curricula.entities import CurriculumItem, CurriculumItemResource
from hyperstate.response import ActorContext
from hyperstate.flash import Flash
from app.projection.curricula.detail import CurriculumDetailProjection

@pytest.fixture
def actor():
    return ActorContext(id="parent-1", roles=["parent"])

@pytest.fixture
def curriculum():
    c = Curriculum(id="CUR-1", name="Math Curriculum", grade_level="1st", description="First grade math")
    
    item1 = CurriculumItem(
        id="ITEM-1",
        curriculum_id="CUR-1",
        sequence=1,
        subject_id="SUB-MATH",
        title="Addition",
        description="Adding numbers",
        day_offset=0,
    )
    item1.resources.append(CurriculumItemResource(id="RES-1", item_id="ITEM-1", resource_type="pdf", title="Worksheet", url="/pdf/math1"))
    c.add_item(item1)
    
    item2 = CurriculumItem(
        id="ITEM-2",
        curriculum_id="CUR-1",
        sequence=2,
        subject_id="SUB-MATH",
        title="Subtraction",
        description="Subtracting numbers",
        day_offset=1,
    )
    c.add_item(item2)
    return c

class TestCurriculumDetailProjection:
    def test_build_detail_projection(self, curriculum, actor):
        projection = CurriculumDetailProjection(curriculum=curriculum, actor=actor)
        response = projection.build()
        
        # Title and self
        assert response.title == "Math Curriculum"
        assert response.self_ == "/curricula/CUR-1"
        
        # View context
        assert response.context.domain == "curricula"
        assert response.context.aggregate == "curriculum"
        assert response.context.state == "detail"
        
        # Nav links
        assert len(response.nav) == 1
        assert response.nav[0].label == "All Curricula"
        assert response.nav[0].href == "/curricula"
        assert response.nav[0].rel == "collection"
        
        # Flash
        assert response.flash is None
        
        # Sections
        assert len(response.sections) == 4
        
        # Group section
        group_section = next(s for s in response.sections if s.kind == "group")
        assert len(group_section.sections) == 2
        
        # Properties section
        props_section = next(s for s in group_section.sections if s.kind == "properties")
        assert props_section.title == "Curriculum Details"
        prop_keys = {p.key: p.value for p in props_section.data}
        assert prop_keys["id"] == "CUR-1"
        assert prop_keys["name"] == "Math Curriculum"
        assert prop_keys["description"] == "First grade math"
        assert prop_keys["grade_level"] == "1st"
        
        # Instantiate action section
        instantiate_action = next(s for s in group_section.sections if s.kind == "action")
        assert instantiate_action.key == "instantiate-curriculum"
        assert instantiate_action.method == "POST"
        assert instantiate_action.href == "/curricula/CUR-1/instantiate"
        field_names = {f.name for f in instantiate_action.fields}
        assert "student_id" in field_names
        assert "start_date" in field_names
        
        # List section (Curriculum Items)
        list_section = next(s for s in response.sections if s.kind == "list")
        assert list_section.title == "Curriculum Items"
        assert len(list_section.items) == 2
        
        # Item 1 data
        item1 = list_section.items[0]
        assert item1.data["id"] == "ITEM-1"
        assert item1.data["title"] == "Addition"
        assert item1.data["subject"] == "SUB-MATH"
        assert item1.data["resources"] == "Worksheet"
        assert item1.data["day_offset"] == "+0"
        
        # Item 1 actions
        actions = {a.key: a for a in item1.actions}
        assert "edit-item" in actions
        assert "add-resource" in actions
        assert "remove-item" in actions
        assert actions["edit-item"].method == "POST"
        assert actions["edit-item"].href == "/curricula/CUR-1/items/ITEM-1/edit"
        assert actions["remove-item"].method == "POST"
        assert actions["remove-item"].href == "/curricula/CUR-1/items/ITEM-1/remove"
        
        # Item 2 data
        item2 = list_section.items[1]
        assert item2.data["id"] == "ITEM-2"
        assert item2.data["title"] == "Subtraction"
        assert item2.data["resources"] == "None"
        assert item2.data["day_offset"] == "+1"
        
        # Add item action section
        add_item_action = next(s for s in response.sections if s.kind == "action" and s.key == "add-item")
        assert add_item_action.key == "add-item"
        assert add_item_action.method == "POST"
        assert add_item_action.href == "/curricula/CUR-1/items"
        
        # Reorder items action section
        reorder_items_action = next(s for s in response.sections if s.kind == "action" and s.key == "reorder-items")
        assert reorder_items_action.key == "reorder-items"
        assert reorder_items_action.method == "POST"
        assert reorder_items_action.href == "/curricula/CUR-1/items/reorder"

    def test_build_detail_projection_with_flash(self, curriculum, actor):
        projection = CurriculumDetailProjection(curriculum=curriculum, actor=actor)
        flash = Flash(title="Success", body="Curriculum updated", type="success")
        response = projection.build(flash=flash)
        assert response.flash == flash
        assert response.flash.title == "Success"
        assert response.flash.body == "Curriculum updated"
        assert response.flash.type == "success"
