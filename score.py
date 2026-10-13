"""Score a candidate bill of materials against a corpus case's established ground truth.

WHAT MAKES THIS DIFFERENT FROM THE QUALITY SCORERS ALREADY IN THE TIER. `sbom_quality.assess` and
the bundled independent scorer judge a document on its own terms -- are the identifiers usable, is
the schema valid, is the licence clear. This asks a question neither of them can: **is it right.**
That needs a truth to compare against, which only exists inside this corpus.

THE RULE THE WHOLE THING TURNS ON. A dimension whose ground truth is `not-established` is **not
scored**. It returns None with the reason attached, and the reason is printed. Scoring an unknown
version as zero would manufacture exactly the unreproducible number this corpus exists to replace,
and scoring it as correct would be worse. See benchmark/README.md.

DIMENSIONS 6 AND 7 ARE PROPERTIES OF A RUN, NOT OF A DOCUMENT. Runtime and reproducibility cannot
be read off a file, so they are accepted as measurements from a harness that actually ran the tool
and are reported as given, with their provenance. Absent, they are None -- never zero.

FALSE POSITIVES AND NEGATIVES ARE NAMED, never summarised. A score of "92% precision" tells a
reader nothing they can act on; "reported heap_3 and smsc9220, missed libgcc" tells them what to
fix. The protocol demands it and it is the most useful part of the output.

    python3 benchmark/score.py --list
    python3 benchmark/score.py --case 001-freertos-plus-tcp-mps2 --sbom candidate.cdx.json
    python3 benchmark/score.py --case 001-... --sbom candidate.cdx.json --json
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, 'cases')

NOT_ESTABLISHED = 'not-established'

#: THE BYTES THE TOOL EMITTED, kept so the schema dimension sees the document rather than our
#: parse of it. A schema check over a reparsed object would validate our reader, not their output.
_RAW = {}


def normalise(name):
    """The corpus's matching rule, stated once.

    Lower-cased with every non-alphanumeric character removed, which is the same rule
    `sbom_link._normalise` and the library index seed use. `FreeRTOS-Plus-TCP`,
    `freertos_plus_tcp` and `FreeRTOS Plus TCP` are one name; nothing else is.
    """
    return re.sub(r'[^a-z0-9]', '', str(name or '').lower())


def load_case(case):
    directory = os.path.join(CASES, case)
    if not os.path.isdir(directory):
        sys.exit(f'No such case: {case}. Try --list.')
    with open(os.path.join(directory, 'case.json'), encoding='utf-8') as handle:
        meta = json.load(handle)
    with open(os.path.join(directory, 'ground-truth.json'), encoding='utf-8') as handle:
        truth = json.load(handle)
    return meta, truth


def read_candidate(path):
    """A candidate document's components, as `{'Name', 'Version', 'Licence', 'Evidence'}` rows.

    READ WITH THE TIER'S OWN PARSER where it can be imported, so the corpus scores what the product
    would actually ingest rather than a second, more forgiving reader written for the benchmark. A
    benchmark that parses more generously than the product under test flatters it.
    """
    with open(path, 'rb') as handle:
        raw = handle.read()
    _RAW['bytes'] = raw

    try:
        sys.path.insert(0, os.path.dirname(HERE))
        from cres_t4.service import sbom_formats
    except ImportError:
        sbom_formats = None

    if sbom_formats is not None:
        # `parse` RETURNS (header, components) and its component keys are raw.SBOM_COMPONENT's
        # column names, which is why they are lower-cased here and title-cased below.
        (_header, components) = sbom_formats.parse(raw)
        return [{
            'Name': one.get('name'),
            'Version': one.get('version'),
            'Licence': one.get('license_expression'),
            'Purl': one.get('purl'),
            'Cpe': one.get('cpe'),
            'Raw': one,
        } for one in (components or [])], 'cres_t4.service.sbom_formats'

    # A LAST RESORT, AND IT SAYS SO IN THE OUTPUT. CycloneDX JSON only, because guessing at SPDX
    # here would be the second parser this docstring warns about.
    document = json.loads(raw.decode('utf-8'))
    return [{
        'Name': one.get('name'),
        'Version': one.get('version'),
        'Licence': _fallback_licence(one),
        'Purl': one.get('purl'),
        'Cpe': one.get('cpe'),
        'Raw': one,
    } for one in (document.get('components') or [])], 'fallback CycloneDX JSON reader'


def _fallback_licence(component):
    """A CycloneDX component's licence, for the reader that runs without the product.

    THIS USED TO RETURN NOTHING, AND THAT WAS THE WORST KIND OF BUG THIS CORPUS CAN HAVE. With the
    product unavailable the fallback reported every licence as absent, so `LicenceAccuracy` scored
    **0%** against a document that had them all right -- the corpus blaming a tool for its own
    inability to read. Found by running the corpus standing alone outside the repository, which is
    exactly the condition a published corpus is used in.

    CycloneDX writes a licence two ways and both are ordinary: an SPDX expression, or a list of
    license objects with an `id` or a `name`. Joined with AND, which is what a list on one
    component means.
    """
    licences = component.get('licenses') or []
    if isinstance(licences, dict):                               # a single object, not a list
        licences = [licences]
    found = []
    for one in licences:
        if not isinstance(one, dict):
            continue
        if one.get('expression'):
            found.append(str(one['expression']))
            continue
        inner = one.get('license') or {}
        if isinstance(inner, dict) and (inner.get('id') or inner.get('name')):
            found.append(str(inner.get('id') or inner.get('name')))
    return ' AND '.join(found) or None


def _names_of(entry):
    return {normalise(entry['Name'])} | {normalise(one)
                                         for one in (entry.get('AcceptableNames') or [])}


def match(truth, candidate):
    """Which truth entries were found, which candidate rows matched nothing, by name."""
    pairs, unmatched = {}, []
    remaining = list(truth['Components'])

    for row in candidate:
        got = normalise(row['Name'])
        for entry in remaining:
            if got in _names_of(entry):
                pairs.setdefault(entry['Name'], []).append(row)
                break
        else:
            unmatched.append(row)

    missed = [entry['Name'] for entry in remaining if entry['Name'] not in pairs]
    return pairs, unmatched, missed


def _first_party_names(truth):
    out = set()
    for one in (truth.get('NotComponents') or []):
        out.add(normalise(one['Name']))
        for name in (one.get('ObjectNames') or []):
            out.add(normalise(os.path.splitext(name)[0]))
    return out


def score(truth, candidate, case_dir=None):
    pairs, unmatched, missed = match(truth, candidate)
    found = len(pairs)
    total = len(truth['Components'])

    # 1. PRECISION AND RECALL, with the denominator stated. Precision over what the tool reported,
    #    recall over what actually shipped.
    precision = found / len(candidate) if candidate else None
    recall = found / total if total else None

    # 2. VERSION AND LICENCE ACCURACY, counted ONLY where the truth is established.
    version = _field_accuracy(truth, pairs, 'Version')
    licence = _field_accuracy(truth, pairs, 'Licence')

    # 3. SCOPE ACCURACY. Did the tool claim anything shipped that the linker discarded? The
    #    discarded translation units are named in the truth, so a candidate naming one as a
    #    component -- or naming the feature it implements -- is measurably wrong.
    scope = _scope(truth, unmatched, case_dir)

    # 4. PROVENANCE COVERAGE: the proportion of reported components carrying something inspectable.
    #    A purl or a CPE is an identifier somebody else can look up; a bare name is not.
    with_evidence = sum(1 for row in candidate if row.get('Purl') or row.get('Cpe'))
    provenance = with_evidence / len(candidate) if candidate else None

    return {
        'Case': truth['Case'],
        'GroundTruthVersion': truth['GroundTruthVersion'],
        'Dimensions': {
            'ComponentPrecision': _rounded(precision),
            'ComponentRecall': _rounded(recall),
            'VersionAccuracy': version,
            'LicenceAccuracy': licence,
            'ScopeAccuracy': scope,
            'ProvenanceCoverage': _rounded(provenance),
            'SchemaValidity': _schema(),
            'RuntimeSeconds': None,
            'Reproducible': None,
        },
        'Matched': {name: [row['Name'] for row in rows] for name, rows in pairs.items()},
        'FalsePositives': [row['Name'] for row in unmatched],
        'FalseNegatives': missed,
        'Counts': {'TruthComponents': total, 'Reported': len(candidate), 'Matched': found},
    }


def _schema():
    """Dimension 5, by REUSING the tier's validator rather than writing a second one.

    The earlier version of this scorer refused to score schema validity, on the grounds that a
    second implementation is how two readers come to disagree. That reasoning was right about
    duplication and wrong about the conclusion: `cres_t4.service.schema_validation` already holds
    the published CycloneDX and SPDX schemas and is what the product itself validates with, so
    calling it is reuse. A benchmark that declined to score a dimension it could simply ASK about
    was leaving the card at seven of eight for no reason.

    IT VALIDATES THE BYTES THE TOOL EMITTED, not our parse of them. Re-serialising our own
    component rows and checking those would validate this scorer's reader.
    """
    raw = _RAW.get('bytes')
    if not raw:
        return {'Value': None, 'Reason': 'Not scored: no document bytes were read.'}
    try:
        sys.path.insert(0, os.path.dirname(HERE))
        from cres_t4.service import schema_validation
    except ImportError:
        return {'Value': None,
                'Reason': 'Not scored: cres_t4.service.schema_validation could not be imported, '
                          'so there is nothing to validate against. Run this from the t4 '
                          'repository with cres-aws on PYTHONPATH.'}

    verdict = schema_validation.validate(raw)
    if not verdict.get('Validated'):
        # BUILT WITHOUT A NESTED f-STRING ON PURPOSE. A multi-line f-string carrying the same
        # quote character inside its braces is valid only from Python 3.12 (PEP 701), and this
        # corpus is meant to run on whatever python3 a reader happens to have -- it failed outright
        # on debian:bookworm's 3.11, which is the image its own cases are built in.
        caveat = verdict.get('Caveat') or 'the document could not be checked against a schema'
        return {'Value': None, 'Format': verdict.get('Format'),
                'Reason': 'Not scored: ' + caveat}
    return {
        'Value': 1.0 if verdict.get('Valid') else 0.0,
        'Format': verdict.get('Format'),
        'SpecVersion': verdict.get('SpecVersion'),
        'SchemaUsed': verdict.get('SchemaUsed'),
        'ErrorCount': verdict.get('ErrorCount'),
        # THE FIRST FEW ERRORS, NOT A COUNT. "3 schema errors" is not actionable; the paths are.
        'Errors': (verdict.get('Errors') or [])[:5],
        'Reason': None if verdict.get('Valid') else
                  f"{verdict.get('ErrorCount')} schema error(s) against "
                  f"{verdict.get('SchemaUsed')}",
    }


#: How each dimension reads. Anything absent is a ratio, which is the common case.
_UNITS = {'RuntimeSeconds': 'seconds', 'Reproducible': 'boolean'}


def _formatted(key, value):
    unit = _UNITS.get(key)
    if unit == 'seconds':
        return f'{value:.4f}s (median of the repetitions)'
    if unit == 'boolean':
        return 'yes' if value else 'NO -- equivalent runs produced different bytes'
    return f'{value:.1%}'


def _rounded(value):
    return None if value is None else round(value, 4)


def _field_accuracy(truth, pairs, field):
    """`{Value, Checked, Correct, Reason}` for Version or Licence, skipping unestablished truth."""
    confidence = f'{field}Confidence'
    checked, correct, skipped = 0, 0, []

    for entry in truth['Components']:
        if entry.get(confidence) == NOT_ESTABLISHED or entry.get(field) is None:
            skipped.append(entry['Name'])
            continue
        rows = pairs.get(entry['Name'])
        if not rows:
            continue
        checked += 1
        wanted = normalise(entry[field])
        if any(normalise(row.get(field if field != 'Licence' else 'Licence')) == wanted
               for row in rows):
            correct += 1

    if not checked:
        return {'Value': None, 'Checked': 0, 'Correct': 0,
                'Reason': f'Not scored: no matched component has an established {field.lower()}. '
                          f'Unestablished in this case: {", ".join(skipped) or "none"}.'}
    return {'Value': round(correct / checked, 4), 'Checked': checked, 'Correct': correct,
            'Reason': (f'{len(skipped)} component(s) skipped as {NOT_ESTABLISHED}: '
                       f'{", ".join(skipped)}.' if skipped else None)}


def _discarded_names(entry, case_dir):
    """The object or member names a component was compiled with and did NOT ship.

    READ FROM AN EVIDENCE FILE WHERE THERE IS ONE. Case 001 lists seven discarded objects inline;
    case 002 has eighty-three unpulled archive members, which belong in
    `evidence/members-never-pulled.txt` rather than inflating the truth file. Both are the same
    claim -- compiled, not in the image -- so both reach the scope dimension.
    """
    evidence = entry.get('Evidence') or {}
    names = list(evidence.get('DiscardedNames') or [])

    listed = (evidence.get('Lists') or {}).get('NeverPulled')
    if listed and case_dir:
        path = os.path.join(case_dir, listed)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as handle:
                names += [line.strip() for line in handle if line.strip()]
    return names


def _scope(truth, unmatched, case_dir=None):
    """Did the candidate claim a discarded translation unit shipped?

    THE DIMENSION THIS CORPUS WAS BUILT FOR. Case 001's seven discarded objects are the test: a
    tool that walked the source tree reports their features as present, and the linker says none of
    their bytes are in the image.

    IT RUNS OVER THE UNMATCHED ROWS ONLY, AND MATCHES EXACTLY. The first version of this took every
    reported component and allowed substring matches, which made the honest candidate score 85.7%:
    `freertos` is a substring of `freertosdhcpv6`, so the FreeRTOS kernel -- which shipped, and
    which the ground truth lists as a component -- was read as a claim about a discarded DHCPv6
    unit. A benchmark that penalises a correct answer is worse than no benchmark, so a row that
    matched a real component is a real component and is not examined here, and what remains is
    compared on the whole normalised name.
    """
    discarded = {}
    for entry in truth['Components']:
        for name in _discarded_names(entry, case_dir):
            discarded[normalise(os.path.splitext(name)[0])] = entry['Name']
    if not discarded:
        return {'Value': None, 'Checked': 0,
                'Reason': 'Not scored: this case records no discarded objects, so there is nothing '
                          'a source-tree reading could get wrong.'}

    claimed = []
    for row in unmatched:
        owner = discarded.get(normalise(row['Name']))
        if owner:
            claimed.append({'Reported': row['Name'], 'DiscardedFrom': owner})

    wrong = len(claimed)
    return {
        'Value': round(1 - wrong / len(discarded), 4),
        'Checked': len(discarded),
        'ClaimedShipped': claimed,
        'Reason': (None if not wrong else
                   f'{wrong} of {len(discarded)} discarded units were reported as shipped. The '
                   f'linker put none of their bytes in the image.'),
    }


def render(result, meta, reader):
    out = []
    out.append(f"case          {result['Case']}  (ground truth v{result['GroundTruthVersion']})")
    out.append(f"              {meta['Name']}")
    out.append(f"read with     {reader}")
    out.append('')
    counts = result['Counts']
    out.append(f"components    {counts['Matched']} of {counts['TruthComponents']} matched, "
               f"from {counts['Reported']} reported")
    out.append('')
    out.append('DIMENSIONS')
    for key, value in result['Dimensions'].items():
        if isinstance(value, dict):
            shown = 'not scored' if value.get('Value') is None else f"{value['Value']:.1%}"
            out.append(f"  {key:22} {shown}")
            if value.get('Reason'):
                out.append(f"  {'':22} -- {value['Reason']}")
            # NAMED, BUT NOT 83 LINES OF TERMINAL. The protocol's requirement is that a false
            # claim is identifiable rather than summarised away, and --json carries every one;
            # a human reading a report needs the first few and the count.
            claimed = value.get('ClaimedShipped') or []
            for one in claimed[:10]:
                out.append(f"  {'':22} !! reported {one['Reported']!r}, discarded from "
                           f"{one['DiscardedFrom']}")
            if len(claimed) > 10:
                out.append(f"  {'':22} .. and {len(claimed) - 10} more; --json lists them all")
        elif value is None:
            out.append(f"  {key:22} not measured")
        else:
            # NOT EVERY DIMENSION IS A RATIO, and formatting them as one produced
            # "RuntimeSeconds 0.3%" for 0.0027 seconds and "Reproducible 100.0%" for True. A
            # benchmark reporting a runtime as a percentage is exactly the meaningless number this
            # corpus exists to replace.
            out.append(f"  {key:22} {_formatted(key, value)}")
    out.append('')
    out.append(f"false positives  {', '.join(result['FalsePositives']) or 'none'}")
    out.append(f"false negatives  {', '.join(result['FalseNegatives']) or 'none'}")
    return '\n'.join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case')
    parser.add_argument('--sbom')
    parser.add_argument('--list', action='store_true', help='the cases in this corpus')
    parser.add_argument('--json', action='store_true', help='machine-readable')
    parser.add_argument('--runtime-seconds', type=float,
                        help='measured by a harness that ran the tool; dimension 6')
    parser.add_argument('--repeat-digests', nargs='*',
                        help='digests of N equivalent runs; dimension 7')
    args = parser.parse_args()

    if args.list:
        for name in sorted(os.listdir(CASES)):
            if os.path.isdir(os.path.join(CASES, name)):
                meta, truth = load_case(name)
                print(f"  {name:34} {len(truth['Components'])} components  {meta['Name']}")
        return

    if not (args.case and args.sbom):
        parser.error('name a case and a document: --case <id> --sbom <path>')

    meta, truth = load_case(args.case)
    candidate, reader = read_candidate(args.sbom)
    result = score(truth, candidate, case_dir=os.path.join(CASES, args.case))

    if args.runtime_seconds is not None:
        result['Dimensions']['RuntimeSeconds'] = args.runtime_seconds
    if args.repeat_digests:
        # REPRODUCIBILITY IS ALL-OR-NOTHING, not a percentage. Either the runs produced the same
        # bytes or they did not.
        result['Dimensions']['Reproducible'] = len(set(args.repeat_digests)) == 1

    print(json.dumps(result, indent=2) if args.json else render(result, meta, reader))


if __name__ == '__main__':
    main()
