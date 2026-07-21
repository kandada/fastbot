import pytest

@pytest.fixture(autouse=True)
def _reset_bridge():
    import fastbot.isaac.bridge as bridge_mod
    bridge_mod._bridge_instance = None
    yield
    bridge_mod._bridge_instance = None
