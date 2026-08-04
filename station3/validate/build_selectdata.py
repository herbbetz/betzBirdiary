import json


def transform_labels(
    input_filepath="myLabels.js", output_filepath="birdlabels.js"
):
    with open(input_filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Strip "const validationOptions =" from the start and trailing semicolon
    json_str = content.split("=", 1)[1].rstrip(";").strip()
    data = json.loads(json_str)

    # Map German name (or main key) to latinName
    select_data = {
        key: details.get("latinName", "None") for key, details in data.items()
    }

    # Format the result as a JavaScript file
    output_content = f"const selectData = {json.dumps(select_data, ensure_ascii=False, indent=4)};\n"

    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"Successfully generated {output_filepath}")


if __name__ == "__main__":
    transform_labels()