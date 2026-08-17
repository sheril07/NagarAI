from description_generator import generate_description


category = "road and transportation issue"
issue = "pothole"

description = generate_description(
    category,
    issue
)

print("DESCRIPTION TEST")
print("================")

print("Category:", category)
print("Issue:", issue)
print("Description:", description)