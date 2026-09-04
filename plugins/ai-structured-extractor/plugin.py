import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


class ApiError(RuntimeError):
    pass


class ChatClient:
    def __init__(self, endpoint, api_key, model, timeout=60, retries=2, opener=None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.opener = opener or urllib.request.urlopen

    @classmethod
    def from_env(cls):
        endpoint = os.environ.get("AI_API_URL", "").strip()
        api_key = os.environ.get("AI_API_KEY", "").strip()
        model = os.environ.get("AI_MODEL", "").strip()
        if not endpoint or not api_key or not model:
            raise ApiError("AI_API_URL, AI_API_KEY and AI_MODEL are required")
        return cls(endpoint, api_key, model)

    def complete(self, messages, schema):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "extracted_data",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        for attempt in range(self.retries + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                return message_text(result)
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if not retryable or attempt == self.retries:
                    detail = error.read().decode("utf-8", errors="replace")
                    raise ApiError(f"API returned {error.code}: {detail[:500]}") from error
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt == self.retries:
                    raise ApiError(str(error)) from error
            time.sleep(0.5 * (2 ** attempt))
        raise ApiError("request failed")


def message_text(response):
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise ApiError("response does not contain a message") from error
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    raise ApiError("message content is not text")


def parse_json(value):
    value = value.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        raise ApiError(f"model returned invalid JSON: {error}") from error


def validate(value, schema, path="$"):
    expected = schema.get("type")
    checks = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    if isinstance(expected, list):
        if not any(validate_type(value, item) for item in expected):
            raise ApiError(f"{path} has an unexpected type")
    elif expected in checks and not checks[expected](value):
        raise ApiError(f"{path} must be {expected}")

    if "enum" in schema and value not in schema["enum"]:
        raise ApiError(f"{path} is not an allowed value")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                raise ApiError(f"{path}.{name} is required")
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise ApiError(f"{path} contains unknown fields: {', '.join(sorted(unknown))}")
        for name, item in value.items():
            if name in properties:
                validate(item, properties[name], f"{path}.{name}")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")


def validate_type(value, expected):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def extract(client, text, schema, guidance=""):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text is required")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("schema must describe an object")
    request = {"text": text}
    if guidance:
        request["guidance"] = guidance
    content = client.complete(
        [
            {
                "role": "system",
                "content": "Extract facts from the supplied text. Do not guess missing values.",
            },
            {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
        ],
        schema,
    )
    result = parse_json(content)
    validate(result, schema)
    return result


def run(payload, client=None):
    client = client or ChatClient.from_env()
    return {
        "data": extract(
            client,
            payload.get("text", ""),
            payload.get("schema", {}),
            payload.get("guidance", ""),
        )
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    payload = {
        "text": Path(args.input).read_text(encoding="utf-8"),
        "schema": json.loads(Path(args.schema).read_text(encoding="utf-8")),
    }
    result = run(payload)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
