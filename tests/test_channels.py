from channels import CHANNELS
from personas import PERSONAS

def test_all_channels_have_required_fields():
    required = ["name", "description", "audience_persona_keys", "style_guide"]
    for key, ch in CHANNELS.items():
        for field in required:
            assert field in ch, f"Channel '{key}' missing '{field}'"

def test_channel_persona_keys_exist():
    for ch_key, ch in CHANNELS.items():
        for pk in ch["audience_persona_keys"]:
            assert pk in PERSONAS, f"Channel '{ch_key}' references unknown persona '{pk}'"

def test_at_least_3_channels():
    assert len(CHANNELS) >= 3
