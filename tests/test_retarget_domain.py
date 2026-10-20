
import json
from conftest import ROOT

def test_it_service_desk_profile_has_no_manufacturing_terms_in_agent_or_tool_descriptions():
    profile=json.loads((ROOT/"config"/"profiles"/"it-service-desk.json").read_text())
    text=" ".join([profile["agent"]["description"],profile["agent"]["instructions"],*profile["catalogTools"].values(),*profile["recordsTools"].values()]).lower()
    for term in ["manufacturing","field ops","work order","parts catalog","plant","line inspection"]: assert term not in text


def test_canonical_walkthrough_metadata_is_synced_to_all_image_contexts():
    source = ROOT / "src"
    images = (source / "agents" / "maf", source / "agents" / "langgraph", source / "catalog-mcp", source / "records-api")
    for profile in (ROOT / "config" / "profiles").glob("*.json"):
        for image in images:
            assert (image / "profiles" / profile.name).read_bytes() == profile.read_bytes()


def test_walkthrough_proposals_do_not_claim_unimplemented_evidence():
    for path in (ROOT / "config" / "profiles").glob("*.json"):
        steps = {step["step"]: step for step in json.loads(path.read_text())["walkthrough"]}
        assert "separately" in steps["S1"]["assertion"]
        assert "catalog tools only" in steps["S3"]["prompt"]
        assert "bounded" in steps["S4"]["prompt"] and "not a pass" in steps["S4"]["assertion"]
        assert "missing joins" in steps["S5"]["assertion"]
