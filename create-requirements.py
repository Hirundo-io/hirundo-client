import yaml

with open("environment.yml", "r") as f:
    try:
        dependencies: list[dict] = yaml.safe_load(f)["dependencies"]
        for dep in dependencies:
            if isinstance(dep, dict) and dep.get("pip"):
                pip_requirements = [
                    pip_dep for pip_dep in dep["pip"] if not pip_dep.startswith("-e")
                ]
                break
    except yaml.YAMLError as exc:
        print(exc)
        raise Exception("Failed to parse environment.yaml") from exc

with open("requirements.txt", "w") as f:
    f.write("\n".join(pip_requirements))
