from app.modules.issues.service import tenant_prefix


def test_petropavlovsk_prefix_is_pvl() -> None:
    assert tenant_prefix("petropavlovsk") == "PVL"


def test_unknown_tenant_prefix_uses_first_three_letters() -> None:
    assert tenant_prefix("astana") == "AST"
