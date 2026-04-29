# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from unittest.mock import patch

from agents.input_interpreter_agent import InputInterpreterAgent


def test_input_interpreter_parses_free_text_into_structured_fields() -> None:
    agent = InputInterpreterAgent()

    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
        intent = agent.run(
            {
                "shot_text": (
                    "145 out, into the wind maybe 10-15, ball sitting down a little, "
                    "back pin, I just want middle of the green"
                )
            }
        )

    assert intent.parsed_fields["distance_to_target"] == 145.0
    assert intent.parsed_fields["wind_direction"] == "headwind"
    assert intent.parsed_fields["pin_position"] == "back"
    assert intent.parsed_fields["target_mode"] == "center_green"
    assert "wind_speed" in intent.ambiguous_fields
    assert "lie_type" in intent.ambiguous_fields
    assert intent.user_intent.goal == "middle_of_green"

