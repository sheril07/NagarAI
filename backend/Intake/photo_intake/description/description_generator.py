def generate_description(category, issue):

    if issue:
        return f"{issue.capitalize()} detected in the submitted image."

    if category:
        return f"Potential {category} issue detected in the submitted image."

    return "Unable to determine the issue from the submitted image."