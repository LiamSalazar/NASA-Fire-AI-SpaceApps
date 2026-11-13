from nasa_fire_ai.models import QueryIntent

NS = "https://example.org/nasa-fire-safety#"


def build_sparql(intent: QueryIntent) -> str:
    """Deterministic, parameter-derived query; no model produces SPARQL."""
    terms = ["PREFIX fs: <" + NS + ">", "SELECT DISTINCT ?run WHERE { ?run a fs:ExperimentalRun ."]
    for material in sorted(intent.materials):
        terms.append(f'?run fs:usesSample/fs:madeOf "{material}" .')
    for gravity in sorted(intent.gravity_conditions):
        terms.append(f'?run fs:hasCondition [ fs:conditionType "gravity"; fs:value "{gravity}" ] .')
    if intent.oxygen:
        terms.append(
            f'?run fs:hasCondition [ fs:conditionType "oxygen"; fs:canonicalValue ?o ] . FILTER(?o {intent.oxygen.operator} {intent.oxygen.value / (100 if intent.oxygen.unit == "%" else 1)})'
        )
    return "\n".join(terms + ["}"])
