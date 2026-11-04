# Lokal untersuchtes Format

Es wurden ausschließlich ZIP-Verzeichnismetadaten und `eblocker-config/appModules.json`
gelesen. Die beiden im Projektverzeichnis bereitgestellten Referenzen haben dieselbe
Grundstruktur, jedoch unterschiedliche weitere Archivbestandteile. Diese wurden nicht
geöffnet. Keine Originaldaten, Namen, Domains oder vollständigen JSON-Beispiele sind
in diese Dokumentation oder Tests übernommen worden.

| Beobachtetes Feld | Verwendung |
| --- | --- |
| `modules` | Liste der tatsächlich enthaltenen Module |
| `enabledStates` | Zuordnung stringifizierter Modul-IDs zu booleschen Zuständen |
| `id` | Ganzzahlige Modulkennung |
| `name` | Anzeigename |
| `description` | Sprachzuordnung; bevorzugt `de`, dann `en`, dann erster Text |
| `whitelistedDomains` | Freigegebene Domains als Liste von Strings |
| `whitelistedIPs` | Freigegebene IPs als Liste von Strings |
| `builtin` | Integriertes oder selbst erstelltes Modul |
| `enabled` | Aktivierungszustand, wenn kein Eintrag in `enabledStates` vorhanden |
| `hidden` | Kennzeichnung des internen Webseitenmoduls gemeinsam mit ID und Name |

Webseitenmodul: ID `9998`, Name `INTERNAL_USE_ONLY_SINGLE_ENTRIES_USERDEFINED`,
`builtin=true`, `hidden=true`. Dessen tatsächlich freigegebene Domains/IPs werden
als separate Webseitenzeilen dargestellt. `labels` können veraltete Einträge enthalten
und werden deshalb nicht als Freigaben interpretiert. Auch `blacklistedDomains`,
`enabledPerDefault`, `modified`, `version` und `updatedVersionAvailable` werden nicht
als Freigaben oder Backup-Version interpretiert. Nicht angezeigte JSON-Felder werden
nicht in das Anwendungsmodell übernommen.

`enabledStates` hat bei Widersprüchen Vorrang vor dem Modulzustand. Die Referenzen
enthielten keine solchen Widersprüche; das Verhalten ist ausdrücklich getestet.
Exakte doppelte Domains/IPs werden bei stabiler Reihenfolge zusammengefasst.
Fehlende optionale Listen bedeuten keine Einträge; ungültige vorhandene Feldtypen
führen zu einer verständlichen Fehlermeldung.

Die ZIP-Versionsnummer bezeichnet das ZIP-Format, nicht die eBlocker-Version.
Archivkommentare und Eintragskommentare der Referenzen waren leer. Deshalb lässt sich
unter der Regel „ausschließlich appModules.json“ keine belastbare Versionszuordnung
zu eBlocker 4 oder 5 durchführen. Das Manifest wurde nicht geöffnet. Synthetische Tests
werden bis zur Klärung ebenfalls nicht fälschlich als verifizierte v4/v5-Fixtures bezeichnet.
