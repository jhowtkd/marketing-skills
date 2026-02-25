from vm_webapp.models import Project


def test_project_model_is_backed_by_products_table() -> None:
    assert Project.__tablename__ == "products"
