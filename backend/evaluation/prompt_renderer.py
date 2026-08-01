from evaluation.exceptions import PromptRenderingError


class PromptRenderer:
    """Render the single supported prompt variable without executing format expressions."""

    input_placeholder = "{input}"

    def validate(self, template: str) -> None:
        if self.input_placeholder not in template:
            raise PromptRenderingError("Prompt template must contain the '{input}' placeholder.")

        remainder = template.replace(self.input_placeholder, "")
        if "{" in remainder or "}" in remainder:
            raise PromptRenderingError(
                "Prompt template contains unsupported placeholders or braces."
            )

    def render(self, template: str, input_text: str) -> str:
        self.validate(template)
        rendered = template.replace(self.input_placeholder, input_text)
        if not rendered.strip():
            raise PromptRenderingError("Rendered prompt must not be blank.")
        return rendered
