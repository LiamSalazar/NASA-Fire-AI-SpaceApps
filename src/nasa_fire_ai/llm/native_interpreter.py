"""Bounded minimal NVIDIA interpreter, reusing the existing provider client."""

from time import perf_counter

from openai import OpenAIError

from nasa_fire_ai.llm.interfaces import NvidiaStructuredClient, ProviderFailure
from nasa_fire_ai.query.native_interpreter import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    MinimalInterpretationV2,
)


class NvidiaMinimalInterpreter(NvidiaStructuredClient):
    def interpret_minimal(self, query):
        started = perf_counter()
        self.last_receipt = {
            "model": self.model_identity,
            "prompt_version": PROMPT_VERSION,
            "retries": 0,
            "usage": None,
        }
        try:
            response = self.client.with_options(timeout=40, max_retries=0).chat.completions.create(
                model=self.model_identity,
                temperature=0,
                stream=False,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                response_format={"type": "json_object"},
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            self.last_receipt.update(
                usage=response.usage.model_dump() if response.usage else None,
                served_model=response.model,
                finish_reason=response.choices[0].finish_reason,
            )
            if response.choices[0].finish_reason != "stop":
                raise ValueError("Incomplete interpretation")
            proposal = MinimalInterpretationV2.model_validate_json(
                response.choices[0].message.content
            )
            self.last_receipt["proposal"] = proposal.model_dump(mode="json")
            return proposal
        except (OpenAIError, ValueError, TypeError, IndexError) as error:
            self.last_receipt["error_type"] = type(error).__name__
            raise ProviderFailure(type(error).__name__) from error
        finally:
            self.last_receipt["latency_ms"] = (perf_counter() - started) * 1000
