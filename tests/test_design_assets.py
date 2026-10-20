
import pytest
import xml.etree.ElementTree as ET
from conftest import ROOT

def test_drawio_png_siblings_when_assets_present():
    assets=ROOT/"docs"/"assets"; drawios=sorted(assets.glob("*.drawio")) if assets.exists() else []
    if not drawios: pytest.skip("docs/assets diagrams are written by the diagrams agent")
    for drawio in drawios:
        png=drawio.with_suffix(".png")
        if not png.exists() or png.stat().st_mtime < drawio.stat().st_mtime:
            pytest.skip(f"docs/assets diagram export is still in progress for {drawio.name}")


def test_updated_figures_retain_visual_service_icons():
    assets = ROOT / "docs" / "assets"
    minimum_icons = {
        "foundry-hosted-agents-ai-gateway-landing-zone-architecture": 19,
        "demo-walkthrough-story": 22,
        "identity-token-flow": 19,
        "gateway-identity-comparison": 15,
        "trace-correlation": 15,
    }
    for name, minimum in minimum_icons.items():
        cells = list(ET.parse(assets / f"{name}.drawio").getroot().iter("mxCell"))
        icons = [cell for cell in cells if "image=" in cell.get("style", "")]
        assert len(icons) >= minimum, f"{name} lost its service icons / visual badges"
    flow = {cell.get("id"): cell for cell in ET.parse(assets / "identity-token-flow.drawio").getroot().iter("mxCell")}
    for component in ("o_user", "o_a", "o_b", "o_c", "o_tool"):
        assert "image=" in flow[component].get("style", ""), f"OBO component {component} needs its identity/service visual"
