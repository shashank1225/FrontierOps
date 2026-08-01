import pytest

from evaluation.exceptions import PromptRenderingError
from evaluation.prompt_renderer import PromptRenderer


def test_renderer_replaces_input_without_interpreting_input_braces() -> None:
    renderer = PromptRenderer()

    rendered = renderer.render("Evaluate this input: {input}", "value {not_a_variable}")

    assert rendered == "Evaluate this input: value {not_a_variable}"


@pytest.mark.parametrize(
    "template",
    [
        "No input placeholder",
        "Input: {input} and {unknown}",
        "Input: {input} with a stray brace }",
    ],
)
def test_renderer_rejects_unsupported_templates(template: str) -> None:
    with pytest.raises(PromptRenderingError):
        PromptRenderer().validate(template)
