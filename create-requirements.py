import yaml


def get_requirements(file_name: str) -> list[str]:
    with open(file_name, "r") as f:
        try:
            dependencies: list[dict] = yaml.safe_load(f)["dependencies"]
            for dep in dependencies:
                if isinstance(dep, dict) and dep.get("pip"):
                    return [
                        pip_dep
                        for pip_dep in dep["pip"]
                        if not pip_dep.startswith("-e")
                    ]
                else:
                    continue
            return []
        except yaml.YAMLError as exc:
            print(exc)
            raise Exception("Failed to parse environment.yaml") from exc


pip_requirements = get_requirements("environment.yml")
pip_dev_requirements = get_requirements("dev-environment.yml")

with open("requirements.txt", "w") as f:
    f.write("\n".join(pip_requirements))

with open("dev-requirements.txt", "w") as f:
    f.write("\n".join(pip_requirements) + "\n")
    f.write("\n".join(pip_dev_requirements) + "\n")
