from personas import PERSONAS, REQUIRED_FIELDS

def test_all_personas_have_required_fields():
    assert len(PERSONAS) >= 5
    for key, persona in PERSONAS.items():
        for field in REQUIRED_FIELDS:
            assert field in persona, f"Persona '{key}' missing field '{field}'"

def test_persona_values_are_nonempty():
    for key, persona in PERSONAS.items():
        for field in REQUIRED_FIELDS:
            val = persona[field]
            assert val is not None and val != "", f"Persona '{key}' has empty '{field}'"

def test_trust_in_range():
    for key, persona in PERSONAS.items():
        t = persona["trust_in_institutions"]
        assert 0.0 <= t <= 1.0, f"Persona '{key}' trust={t} not in [0,1]"

def test_sentiment_in_range():
    for key, persona in PERSONAS.items():
        s = persona["sentiment"]
        assert 0.0 <= s <= 1.0, f"Persona '{key}' sentiment={s} not in [0,1]"
