import json


def parse_json(text):

    try:
        return json.loads(text)

    except Exception:

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:

            return json.loads(
                text[start:end+1]
            )

        raise ValueError(
            "Invalid JSON"
        )
