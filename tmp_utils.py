from yaml import safe_load, safe_dump


def save_yaml(file_path, data):
    with open(file_path, "w", encoding="utf8") as file_:
        safe_dump(data, file_, default_flow_style=False, allow_unicode=True)


def load_yaml(file_path):
    with open(file_path, "r") as file_:
        return safe_load(file_)
