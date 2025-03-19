def read_readme(file_path):
    """Reads the content of a README file."""
    with open(file_path, 'r') as file:
        return file.read()

def save_executable(file_path, content):
    """Saves the given content as an executable installation script."""
    with open(file_path, 'w') as file:
        file.write(content)
    # Make the file executable (Unix-based systems)
    import os
    os.chmod(file_path, 0o755)