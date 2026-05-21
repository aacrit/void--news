# /history-enrich -- Source Enrichment Workflow

You orchestrate automated source discovery for void --history events using the source enricher CLI.

## Workflow

```
[source enricher CLI] (automated API queries)
  -> media-archaeologist (review images/primary sources)
  -> history-curator (review scholarly sources)
  -> historiographic-auditor (validate source diversity)
```

### Stage 1 -- Enrichment Run

Run the source enricher CLI for the target event(s):

```bash
# Single event
python3 pipeline/history/source_enricher.py --event <slug>

# All events
python3 pipeline/history/source_enricher.py --all

# Specific categories
python3 pipeline/history/source_enricher.py --event <slug> --category scholarly,images,primary
```

Output goes to `data/history/enrichment/<slug>.json`. Review the JSON before proceeding.

### Stage 2 -- Media Review

Launch **media-archaeologist** to review enrichment results:
- Apply Context Protocol to each image/primary source candidate
- Verify rights status (public domain, CC, fair use)
- Assess visual bias across perspectives
- Incorporate approved items into event YAML media entries

### Stage 3 -- Scholarly Review

Launch **history-curator** to review scholarly results:
- Evaluate relevance and citation count
- Update perspective source lists in YAML
- Add new primary source quotes from discovered documents
- Flag recent revisionist scholarship for perspective updates

### Stage 4 -- Diversity Validation

Launch **historiographic-auditor** (read-only) to confirm:
- Source diversity improved (not just Western/Anglophone additions)
- Multiple archive traditions represented
- No perspective over-sourced relative to others

## Available APIs (15 total, all $0)

| Category | APIs | Auth Required |
|----------|------|---------------|
| scholarly | OpenAlex, Semantic Scholar, Crossref | None |
| primary | Library of Congress, Europeana, DPLA, Gallica | Europeana/DPLA need free key |
| images | Wikimedia Commons, Smithsonian | Smithsonian needs free key |
| wikidata | Wikidata SPARQL, Slave Voyages | None |
| geodata | Wikidata Geo, Pleiades | None |
| statistics | World Bank | None |
| oral_history | Curated collection references | None |

Check API readiness: `python3 pipeline/history/source_enricher.py --list-apis`

## Final Report

```
## Source Enrichment Report
- **Event(s)**: [slugs]
- **APIs queried**: [count] / 15
- **Results found**: [count]
- **Images approved**: [count] (media-archaeologist)
- **Scholarly sources added**: [count] (history-curator)
- **Source diversity**: PASS / NEEDS WORK (historiographic-auditor)
```
