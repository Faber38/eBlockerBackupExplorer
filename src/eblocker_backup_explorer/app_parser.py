"""Validierung des lokal beobachteten appModules-Schemas, ohne Fremdfelder."""
from dataclasses import dataclass

WEBSITE_MODULE = "INTERNAL_USE_ONLY_SINGLE_ENTRIES_USERDEFINED"


class AppDataError(ValueError):
    """Ungültige oder nicht unterstützte App-Daten (ohne Nutzdaten im Fehler)."""


@dataclass(frozen=True)
class App:
    name: str
    description: str
    domains: tuple[str, ...]
    enabled: bool
    builtin: bool
    website: bool = False

    @property
    def status(self) -> str:
        return "Aktiviert" if self.enabled else "Deaktiviert"

    @property
    def kind(self) -> str:
        return "Webseite" if self.website else ("Integriert" if self.builtin else "Eigene App")

    def matches(self, query: str) -> bool:
        return query.casefold() in "\n".join((self.name, self.description, *self.domains)).casefold()


def _strings(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise AppDataError("Ungültige Domain-/IP-Liste in appModules.json.")
    return value


def parse_apps(data: object) -> tuple[App, ...]:
    if not isinstance(data, dict) or not isinstance(data.get("modules"), list):
        raise AppDataError("appModules.json enthält keine gültige Modulliste.")
    states = data.get("enabledStates", {})
    if not isinstance(states, dict) or any(type(v) is not bool for v in states.values()):
        raise AppDataError("Ungültige Aktivierungszustände in appModules.json.")
    result = []
    seen_ids = set()
    for module in data["modules"]:
        if not isinstance(module, dict):
            raise AppDataError("Ungültiger Moduleintrag in appModules.json.")
        if type(module.get("id")) is not int or module["id"] in seen_ids:
            raise AppDataError("Fehlende oder doppelte Modul-ID in appModules.json.")
        seen_ids.add(module["id"])
        if not isinstance(module.get("name"), str) or not module["name"].strip():
            raise AppDataError("Fehlender App-Name in appModules.json.")
        for field in ("enabled", "builtin", "hidden"):
            if type(module.get(field)) is not bool:
                raise AppDataError("Fehlende oder ungültige Modulkennzeichnung in appModules.json.")
        description = module.get("description", {})
        if not isinstance(description, dict) or any(not isinstance(v, str) for v in description.values()):
            raise AppDataError("Ungültige App-Beschreibung in appModules.json.")
        text = description.get("de") or description.get("en") or next(iter(description.values()), "")
        domains = tuple(dict.fromkeys(
            _strings(module.get("whitelistedDomains", [])) + _strings(module.get("whitelistedIPs", []))
        ))
        enabled = states.get(str(module["id"]), module["enabled"])
        website = (module["id"] == 9998 and module["name"] == WEBSITE_MODULE
                   and module["builtin"] and module["hidden"])
        if website:
            # Nur tatsächlich freigegebene Werte, keine möglicherweise veralteten labels.
            result.extend(App(d, "", (d,), enabled, False, True) for d in domains)
        else:
            result.append(App(module["name"], text, domains, enabled, module["builtin"]))
    return tuple(result)
