from prompts import (
    build_persona_prompt,
    INTERVIEWER_SYSTEM,
    ANALYST_SYSTEM,
    EDITOR_SYSTEM,
    VALIDATOR_SYSTEM,
    EXTRACTOR_SYSTEM,
)
from personas import PERSONAS

def test_build_persona_prompt_contains_name():
    prompt = build_persona_prompt(PERSONAS["valentina"])
    assert "Валентина" in prompt
    assert "67" in prompt or "Воронеж" in prompt

def test_all_system_prompts_are_nonempty_strings():
    for name, prompt in [
        ("INTERVIEWER", INTERVIEWER_SYSTEM),
        ("ANALYST", ANALYST_SYSTEM),
        ("EDITOR", EDITOR_SYSTEM),
        ("VALIDATOR", VALIDATOR_SYSTEM),
        ("EXTRACTOR", EXTRACTOR_SYSTEM),
    ]:
        assert isinstance(prompt, str), f"{name} is not a string"
        assert len(prompt) > 100, f"{name} is too short ({len(prompt)} chars)"

def test_persona_prompt_includes_key_fields():
    prompt = build_persona_prompt(PERSONAS["sergey"])
    assert "Челябинск" in prompt
