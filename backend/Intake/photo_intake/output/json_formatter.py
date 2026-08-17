import json


def create_output(
    category,
    issue,
    description,
    severity_features
):

    output = {
        "input_type": "photo",
        "category": category,
        "issue": issue,
        "description": description,
        "severity_features": severity_features
    }

    return output


def save_json(data, output_path):

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    print(f"JSON saved to: {output_path}")