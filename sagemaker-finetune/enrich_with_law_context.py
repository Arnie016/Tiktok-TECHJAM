import json
import re
import os
import boto3
from tqdm import tqdm

INPUT_FILES = ['data/train.cleaned.jsonl', 'data/train_refined.jsonl']
OUTPUT_FILE = 'data/train.lawcontext.jsonl'
INDEX_ID = '2885d201-f5ab-4f85-96cf-555c1fc6ff07'
REGION = 'us-west-2'
TOP_K = 5
MIN_SNIPPET_CHARS = 80
MIN_SNIPPETS = 3
MAX_SNIPPETS = 5
MAX_SNIPPET_CHARS = 500
MAX_QUERY_CHARS = 950  # keep well under Kendra 1000-char limit

kendra = boto3.client('kendra', region_name=REGION)

_CITATION_PATTERNS = [
    re.compile(r'(Art\.?\s*\d+[a-z]?(?:\(\d+\))?)', re.I),
    re.compile(r'(Article\s*\d+[a-z]?(?:\(\d+\))?)', re.I),
    re.compile(r'(Recital\s*\d+)', re.I),
    re.compile(r'(§\s*\d+[\w\-]*)'),
    re.compile(r'(\b\d+\s*U\.?S\.?C\.?\s*§?\s*\d+[\w\-]*)', re.I),
    re.compile(r'(Section\s*\d+[\w\-]*)', re.I),
]
_DATE_PATTERN = re.compile(r'\b(20\d{2}|19\d{2})\b')

# Ask Kendra for extra attributes when available
CUSTOM_ATTR_KEYS = [
    'doc_type', 'platform', 'jurisdiction_hint', 'feature_tags',
    'date_iso', 'version', 'law_refs', 'confidence'
]
REQUESTED_DOC_ATTRS = [
    '_source_uri', '_document_title', '_file_type', '_language_code',
    '_excerpt_page_number', '_created_at', '_last_updated_at',
    *CUSTOM_ATTR_KEYS
]


def _extract_meta_from_text(text: str):
    citation = None
    section = None
    article = None
    date = None

    for pat in _CITATION_PATTERNS:
        m = pat.search(text or '')
        if m and not citation:
            citation = m.group(1)
            low = citation.lower()
            if low.startswith('art') or low.startswith('article'):
                article = citation
            if low.startswith('section') or citation.strip().startswith('§'):
                section = citation
    dm = _DATE_PATTERN.search(text or '')
    if dm:
        date = dm.group(1)

    return citation, article, section, date


def _title_text(title_field):
    if isinstance(title_field, dict):
        return title_field.get('Text')
    if isinstance(title_field, str):
        return title_field
    return None


def _infer_simple_attrs(title: str, snippet: str):
    """Very light heuristics to infer platform/jurisdiction/law_refs when absent."""
    out = {}
    t = (title or '').lower()
    s = (snippet or '').lower()
    # platform
    for name in ['tiktok', 'instagram', 'facebook', 'youtube', 'snapchat', 'reddit']:
        if name in t or name in s:
            out['platform'] = name
            break
    # jurisdiction_hint
    if any(word in s for word in ['european union', 'eu regulation', 'digital services act']):
        out['jurisdiction_hint'] = 'eu'
    elif 'florida' in s or 'f.s.' in s:
        out['jurisdiction_hint'] = 'florida'
    elif 'utah' in s:
        out['jurisdiction_hint'] = 'utah'
    elif 'california' in s or 'ccpa' in s:
        out['jurisdiction_hint'] = 'california'
    elif 'u.s.c' in s or 'united states code' in s:
        out['jurisdiction_hint'] = 'us_federal'
    # law_refs
    refs = []
    if 'digital services act' in s or 'dsa' in s:
        refs.append('DSA')
    if '2258a' in s:
        refs.append('18 USC 2258A')
    if '501.1738' in s:
        refs.append('FL 501.1738')
    if refs:
        out['law_refs'] = refs
    return out


def _trim_snippet(snippet: str) -> str:
    text = ' '.join((snippet or '').split())
    if len(text) <= MAX_SNIPPET_CHARS:
        return text
    return text[:MAX_SNIPPET_CHARS].rstrip() + '…'


def get_law_snippets(query, top_k=TOP_K):
    qtext = (query or '')[:MAX_QUERY_CHARS]
    response = kendra.query(
        IndexId=INDEX_ID,
        QueryText=qtext,
        PageSize=top_k,
        RequestedDocumentAttributes=REQUESTED_DOC_ATTRS
    )
    items = []
    seen = set()

    def try_add(result, relax: bool = False):
        excerpt = result.get('DocumentExcerpt', {}).get('Text')
        if not excerpt:
            return False
        if not relax and len(excerpt.strip('. \n\t')) < MIN_SNIPPET_CHARS:
            return False
        title = _title_text(result.get('DocumentTitle'))
        uri = result.get('DocumentURI')
        doc_id = result.get('DocumentId')
        attrs_raw = result.get('DocumentAttributes', []) or []
        attrs = {}
        for a in attrs_raw:
            key = a.get('Key')
            val = a.get('Value')
            if isinstance(val, dict):
                for k, v in val.items():
                    if v is not None:
                        attrs[key] = v
                        break
            else:
                attrs[key] = val
        citation, article, section, date = _extract_meta_from_text(excerpt or '')
        page = attrs.get('_excerpt_page_number') or attrs.get('PageNumber') or attrs.get('page')
        source = attrs.get('_source_uri') or attrs.get('SourceUri') or attrs.get('source')
        # Dedupe by (uri or doc_id) + normalized snippet
        norm_snip = ' '.join(excerpt.split())[:300]
        dedup_key = (uri or doc_id or title, norm_snip)
        if dedup_key in seen:
            return False
        seen.add(dedup_key)

        # Collect custom attributes
        custom = {k: attrs.get(k) for k in CUSTOM_ATTR_KEYS if attrs.get(k) is not None}
        # Light inference if missing
        inferred = _infer_simple_attrs(title, excerpt)
        for k, v in inferred.items():
            custom.setdefault(k, v)

        item = {
            'title': title,
            'citation': citation,
            'article': article,
            'section': section,
            'date': date,
            'uri': uri,
            'page': page,
            'source': source,
            'snippet': _trim_snippet(excerpt),
            **custom,
        }
        items.append(item)
        return True

    # First pass with standard thresholds
    for result in response.get('ResultItems', []):
        if len(items) >= MAX_SNIPPETS:
            break
        try_add(result, relax=False)

    # Fallback: relax filters to ensure at least MIN_SNIPPETS
    if len(items) < MIN_SNIPPETS:
        for result in response.get('ResultItems', []):
            if len(items) >= MIN_SNIPPETS:
                break
            try_add(result, relax=True)

    return items


def _omit_nulls(d):
    return {k: v for k, v in d.items() if v not in (None, '', [], {})}


def build_structured_context(snippet_dicts):
    minimal = []
    for s in snippet_dicts:
        minimal.append(_omit_nulls({
            'title': s.get('title'),
            'citation': s.get('citation'),
            'article': s.get('article'),
            'section': s.get('section'),
            'date': s.get('date'),
            'uri': s.get('uri'),
            'page': s.get('page'),
            'source': s.get('source'),
            'doc_type': s.get('doc_type'),
            'platform': s.get('platform'),
            'jurisdiction_hint': s.get('jurisdiction_hint'),
            'feature_tags': s.get('feature_tags'),
            'date_iso': s.get('date_iso'),
            'version': s.get('version'),
            'law_refs': s.get('law_refs'),
            'confidence': s.get('confidence'),
            'snippet': s.get('snippet'),
        }))
    minimal = [m for m in minimal if m]
    return json.dumps(minimal, ensure_ascii=False)


def _extract_feature_description_only(feature_raw: str) -> str:
    # Use only the Feature Description line, not the entire block
    if 'Feature Description:' in feature_raw:
        after = feature_raw.split('Feature Description:', 1)[1]
        first_line = after.splitlines()[0].strip()
        return first_line[:MAX_QUERY_CHARS]
    # Fallback to first line of input
    return feature_raw.splitlines()[0][:MAX_QUERY_CHARS]


seen_examples = set()

with open(OUTPUT_FILE, 'w') as outfile:
    for input_path in INPUT_FILES:
        if not os.path.exists(input_path):
            continue
        with open(input_path, 'r') as infile:
            for line in tqdm(infile, desc=f'Enriching from {input_path}'):
                example = json.loads(line)
                feature_raw = example.get('input', '')
                key = (example.get('instruction', ''), feature_raw, example.get('output', ''))
                if key in seen_examples:
                    continue
                seen_examples.add(key)

                # If already enriched with structured context, just passthrough
                if 'Law Context (structured JSON):' in feature_raw:
                    outfile.write(json.dumps(example, ensure_ascii=False) + '\n')
                    continue

                query = _extract_feature_description_only(feature_raw)
                snippets = get_law_snippets(query, top_k=TOP_K)
                structured = build_structured_context(snippets)

                new_input = f"{feature_raw}\n\nLaw Context (structured JSON):\n{structured}"

                enriched = {
                    'instruction': example['instruction'],
                    'input': new_input,
                    'output': example['output']
                }
                outfile.write(json.dumps(enriched, ensure_ascii=False) + '\n')
