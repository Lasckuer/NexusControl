from typing import Dict

ALIASES: Dict[str, str] = {
    "dhczomw": "Nexus Control",
    "flzrgsoj": "Node Notes",
    "ud552te": "Personal Finance Bot",
    "seaweedfs-admin": "SeaweedFS Admin",
    "seaweedfs-master": "SeaweedFS Master",
    "n6welm1": "Redis",
    "Ogufwalvk": "Synapse",
    "nexus_control": "Nexus Control",
    "nexus-control": "Nexus Control",
}

def prettify_name(raw_name: str) -> str:
    """
    Преобразует техническое имя контейнера в красивое читаемое название.
    Если имя совпадает с алиасом, возвращает алиас.
    Если содержит хеши или суффиксы compose, очищает их.
    """
    if not raw_name:
        return "Unknown"

    for key, nice_name in ALIASES.items():
        if key.lower() in raw_name.lower():
            return nice_name

    parts = raw_name.split('-')
    if len(parts) > 1 and len(parts[-1]) > 10:
        cleaned = " ".join(parts[:-1])
        return cleaned.replace('_', ' ').title()

    return raw_name.replace('-', ' ').replace('_', ' ').title()
