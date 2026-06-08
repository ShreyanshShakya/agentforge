import os
import re


def save_generated_project(
    content,
    output_dir="output/project"
):

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    pattern = (
        r"FILE:\s*(.*?)\n"
        r"(.*?)"
        r"END_FILE"
    )

    matches = re.findall(
        pattern,
        content,
        re.DOTALL
    )

    for filename, file_content in matches:

        filename = filename.strip()

        path = os.path.join(
            output_dir,
            filename
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                file_content.strip()
            )

        print(
            f"Created: {path}"
        )
