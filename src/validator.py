import re

ISO_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
TIMESTAMP = re.compile(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}')
CITATION = re.compile(r'\[([^\]]+)\]')
NUMBER = re.compile(r'\d+(?:,\d{3})*(?:\.\d+)?')
ALLOWED_NUMBERS = {30.0, 500.0}  # the 30-day window comes from the query, not the packet
VERDICT_WORDS = ['fraud', 'compromis', 'stolen', 'criminal', 'unauthorized']
JUDGMENT_WORDS = ['low', 'high', 'unusual', 'normal', 'suspicious']
TEXT_FIELDS = ['summary', 'history_reliability', 'confidence_note']
LIST_FIELDS = ['reasons_to_escalate', 'reasons_for_false_positive']


def _resolve(packet, path):
    node = packet
    for part in path.strip().split('.'):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False
    return True


def _collect(node, nums, strings):
    if isinstance(node, bool) or node is None:
        return
    if isinstance(node, (int, float)):
        nums.add(float(node))
    elif isinstance(node, str):
        strings.append(node)
        for year in re.findall(r'\b\d{4}\b', node):
            nums.add(float(year))
    elif isinstance(node, dict):
        for v in node.values():
            _collect(v, nums, strings)
    elif isinstance(node, list):
        nums.add(float(len(node)))
        for v in node:
            _collect(v, nums, strings)


def validate_output(output, packet):
    """Return {'errors': [...], 'warnings': [...]}. Any error means: show raw evidence only."""
    errors, warnings = [], []
    nums, strings = set(), []
    _collect(packet, nums, strings)

    texts = [(f, output[f]) for f in TEXT_FIELDS]
    for f in LIST_FIELDS:
        for i, item in enumerate(output[f]):
            texts.append((f'{f}[{i}]', item))

    for name, text in texts:
        cites = CITATION.findall(text)
        if not cites:
            errors.append(f'{name}: no citation')
        for group in cites:
            for path in group.split(','):
                if not _resolve(packet, path):
                    errors.append(f'{name}: unknown field [{path.strip()}]')
                elif 'syn_' in path:
                    warnings.append(f'{name}: cites synthetic field [{path.strip()}]')
        body = CITATION.sub('', text)
        for ts in TIMESTAMP.findall(body):
            if not any(x.replace('T', ' ').startswith(ts.replace('T', ' ')) for x in strings):
                errors.append(f'{name}: timestamp {ts} not in evidence')
        body = TIMESTAMP.sub('', body)
        for d in ISO_DATE.findall(body):
            if not any(s.startswith(d) for s in strings):
                errors.append(f'{name}: date {d} not in evidence')
        body = ISO_DATE.sub('', body)
        for tok in NUMBER.findall(body):
            decimals = len(tok.split('.')[1]) if '.' in tok else 0
            value = float(tok.replace(',', ''))
            if value not in ALLOWED_NUMBERS and not any(round(n, decimals) == value for n in nums):
                errors.append(f'{name}: number {tok} not in evidence')
        low = body.lower()
        for w in VERDICT_WORDS:
            if w in low:
                warnings.append(f'{name}: verdict-like word "{w}"')
        for w in JUDGMENT_WORDS:
            if re.search(rf'\b{w}\b', low):
                warnings.append(f'{name}: judgment word "{w}"')
    return {'errors': errors, 'warnings': warnings}
