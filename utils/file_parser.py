import re


def extract_files(response):

    pattern = r"FILE:\s*(.*?)\n```(?:\w+)?\n(.*?)```"

    matches = re.findall(
        pattern,
        response,
        re.DOTALL
    )

    return matches

import os

os.makedirs(
    "output/project",
    exist_ok=True
)

files = extract_files(code_output)

for filename, content in files:

    path = f"output/project/{filename}"

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)
