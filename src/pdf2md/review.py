"""PDF evidence and conservative algorithm transcription, without author sources.

MinerU JSON and markdown.raw.md are immutable parser evidence. Formula heuristics
only flag review candidates; they never rewrite mathematical expressions.
"""
from __future__ import annotations

from collections import Counter
from html import unescape
import json
import math
from pathlib import Path
import re
import unicodedata

import pypdfium2 as pdfium

REVIEW_VERSION = 1
ALGORITHM_DIV = re.compile(r'<div\b[^>]*class=["\']docvortex-algorithm["\'][^>]*>\s*(.*?)\s*</div>', re.S)


def canonical(text):
    return ' '.join(unescape(text).split())


def canonical_algorithm(text):
    # MinerU escapes underscores in JSON text outside math, but removes those
    # escapes when rendering the HTML algorithm. Never normalize LaTeX itself.
    pieces = re.split(r'(?<!\\)(\$\$|\$)', unescape(text))
    delimiter = None
    for index, piece in enumerate(pieces):
        if piece in ('$', '$$'):
            delimiter = None if delimiter == piece else piece
        elif delimiter is None:
            pieces[index] = re.sub(r'\\+([_*`])', r'\1', piece)
    return canonical(''.join(pieces))


def word_counts(text):
    return Counter(re.findall(r'[a-z]{3,}', unicodedata.normalize('NFKC', text).casefold()))


def native_algorithm_decision(native, recognized):
    """Require matching title, numbered steps and vocabulary before using text.

    This checks extraction reliability, not equivalence of mathematical layout.
    Superscripts/subscripts in the plain text still require the original crop.
    """
    reasons = []
    if len(native.strip()) < 80:
        reasons.append('native_text_missing_or_short')
    if any(unicodedata.category(char) in ('Co', 'Cs', 'Cc') and not char.isspace()
           or char == '\ufffd' for char in native):
        reasons.append('native_text_has_invalid_glyphs')
    title = lambda text: canonical(unicodedata.normalize('NFKC', text).splitlines()[0]).casefold() if text.strip() else ''
    if title(native) != title(recognized):
        reasons.append('algorithm_title_mismatch')
    step_ids = lambda text: re.findall(r'^\s*(\d{1,3})\s+', text, re.M)
    native_ids, recognized_ids = step_ids(native), step_ids(recognized)
    if len(native_ids) < 2 or native_ids != recognized_ids:
        reasons.append('numbered_steps_mismatch')
    source, target = word_counts(native), word_counts(recognized)
    overlap = sum((source & target).values()) / sum(source.values()) if source else 0
    if overlap < .65:
        reasons.append('native_vocabulary_mismatch')
    return not reasons, reasons, round(overlap, 4)


def latex_flags(latex, *, algorithm=False, context=''):
    """A short review queue, not a LaTeX correctness validator or accuracy score."""
    flags, stack = [], []
    for index, char in enumerate(latex):
        if char not in '{}':
            continue
        backslashes, previous = 0, index - 1
        while previous >= 0 and latex[previous] == '\\':
            backslashes += 1
            previous -= 1
        if backslashes % 2:
            continue
        if char == '{':
            stack.append(char)
        elif not stack:
            flags.append('unbalanced_braces')
            break
        else:
            stack.pop()
    if stack:
        flags.append('unbalanced_braces')
    if '\ufffd' in latex or '??' in latex:
        flags.append('replacement_or_unknown_characters')
    if len(re.findall(r'\\left\b', latex)) != len(re.findall(r'\\right\b', latex)):
        flags.append('unpaired_left_right')
    environments = []
    for command, name in re.findall(r'\\(begin|end)\s*\{([^{}]+)\}', latex):
        if command == 'begin':
            environments.append(name)
        elif not environments or environments.pop() != name:
            flags.append('mismatched_environment')
    if environments:
        flags.append('mismatched_environment')
    if algorithm and re.search(r'\\inf(?![A-Za-z])', latex) and re.search(r'\bthen\b', context):
        flags.append('possible_if_read_as_inf')
    if algorithm and 'argmin' in context and re.search(r'\\(?:mathbf|mathfrak)\s*\{\s*[1l]\s*\}\s*_', latex):
        flags.append('possible_argmin_subscript_artifact')
    return list(dict.fromkeys(flags))


def valid_bbox(bbox):
    return (isinstance(bbox, (list, tuple)) and len(bbox) == 4
            and all(isinstance(v, (int, float)) and math.isfinite(v) for v in bbox)
            and 0 <= bbox[0] < bbox[2] <= 1 and 0 <= bbox[1] < bbox[3] <= 1)


def native_text(page, bbox):
    if not valid_bbox(bbox) or page.get_rotation() != 0:
        return ''
    width, height = page.get_size()
    textpage = page.get_textpage()
    try:
        result = textpage.get_text_bounded(left=bbox[0]*width, bottom=(1-bbox[3])*height,
                                          right=bbox[2]*width, top=(1-bbox[1])*height)
        return '\n'.join(line.rstrip() for line in result.replace('\r', '').splitlines() if line.strip()).strip()
    finally:
        textpage.close()


def save_region(page, bbox, path):
    """Render only the PDF region at 216 dpi, padded by two PDF points."""
    width, height = page.get_size()
    left = max(0., bbox[0]*width - 2)
    top = max(0., bbox[1]*height - 2)
    right = min(width, bbox[2]*width + 2)
    bottom = min(height, bbox[3]*height + 2)
    bitmap = page.render(scale=3, crop=(left, height-bottom, width-right, top))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        bitmap.to_pil().save(path)
    finally:
        bitmap.close()


def inline_equations(block):
    content = block.get('content')
    if isinstance(content, list):
        for item in content:
            if item.get('type') == 'equation_inline':
                yield item.get('content', '')
            else:
                yield from inline_equations(item)


def code_fence(text, language='text'):
    runs = [len(match.group()) for match in re.finditer(r'`+', text)]
    marker = '`' * max(3, max(runs, default=0) + 1)
    return f'{marker}{language}\n{text}\n{marker}'


def enhance(pdf: Path, md: Path, *, page_images=True, algorithm_text='native'):
    """Add source crops/review inventory and replace only verified algorithm blocks.

    The caller works in a fresh staging directory. Repeated calls always start
    from markdown.raw.md so review notes and replacements are idempotent.
    """
    raw_path = md.with_name('markdown.raw.md')
    if not raw_path.exists():
        raw_path.write_bytes(md.read_bytes())
    original = raw_path.read_text(encoding='utf-8')
    middle = json.loads(md.with_name('middle_json.json').read_text(encoding='utf-8'))
    structured = json.loads(md.with_name('structured_content.json').read_text(encoding='utf-8'))
    source_blocks = {(page['page_idx'], number): block for page in structured.get('pages', [])
                     for number, block in enumerate(page.get('blocks', []))}
    candidates = list(ALGORITHM_DIV.finditer(original))
    claimed, replacements, algorithms, formulas, regions = set(), [], [], [], {}
    document = pdfium.PdfDocument(pdf)
    try:
        for page_data in middle.get('pages', []):
            page_idx = page_data['page_idx']
            page = document[page_idx]
            try:
                for number, block in enumerate(page_data.get('blocks', [])):
                    bbox = block.get('bbox')
                    algorithm = block.get('type') == 'code' and block.get('sub_type') == 'algorithm'
                    recognized = source_blocks.get((page_idx, number), {}).get('content', '')
                    if not isinstance(recognized, str):
                        recognized = ''
                    group_id = f'p{page_idx+1:04d}-block{number:03d}'
                    algorithm_record = None
                    if algorithm:
                        native = native_text(page, bbox)
                        accepted, reasons, overlap = native_algorithm_decision(native, recognized)
                        native_ok = accepted and algorithm_text == 'native'
                        matches = [index for index, match in enumerate(candidates)
                                   if index not in claimed and canonical_algorithm(match.group(1)) == canonical_algorithm(recognized)]
                        algorithm_record = {
                            'id': f'algorithm-{len(algorithms)+1:04d}', 'page_number': page_idx+1,
                            'block_number': number, 'bbox': bbox, 'ocr_text': recognized,
                            'native_text': native, 'native_accepted': accepted,
                            'native_rejection_reasons': reasons, 'native_vocabulary_overlap': overlap,
                            'text_source': 'native_pdf' if native_ok else 'mineru_ocr',
                            'markdown_replaced': bool(matches),
                            'caveat': 'Plain text flattens subscripts and superscripts; use the original crop for mathematical layout.',
                        }
                        if valid_bbox(bbox):
                            region = f'regions/{group_id}-algorithm.png'
                            save_region(page, bbox, md.parent/region)
                            algorithm_record['source_crop'] = region
                            regions[group_id] = region
                        else:
                            algorithm_record['native_rejection_reasons'].append('source_bbox_unavailable')
                        if matches:
                            selected = matches[0]
                            claimed.add(selected)
                            chosen = candidates[selected]
                            source_note = 'Native PDF text; check mathematical layout against the original.' if native_ok else 'OCR transcription; check against the original.'
                            body = code_fence(native) if native_ok else chosen.group()
                            region = algorithm_record.get('source_crop')
                            evidence = f'\n\n![Original algorithm, page {page_idx+1}]({region})' if region else ''
                            body = (f'<!-- pdf2md:{algorithm_record["id"]} -->\n'
                                    f'> {source_note} [Review](review.md#{algorithm_record["id"]}).\n\n'
                                    + body + evidence)
                            replacements.append((chosen.start(), chosen.end(), body))
                        else:
                            algorithm_record['text_source'] = 'mineru_ocr'
                        algorithms.append(algorithm_record)
                    entries = []
                    if block.get('type') == 'equation':
                        entries.append(('display', block.get('content', '')))
                    entries.extend(('inline', latex) for latex in inline_equations(block))
                    for kind, latex in entries:
                        flags = latex_flags(latex, algorithm=algorithm, context=recognized)
                        record = {
                            'id': f'formula-{len(formulas)+1:05d}', 'kind': kind,
                            'page_number': page_idx+1, 'block_number': number,
                            'bbox': bbox, 'bbox_scope': 'equation' if kind == 'display' else 'containing_block',
                            'latex': latex, 'flags': flags, 'semantic_accuracy': 'unverified',
                            'page_reference': f'page_index.md#page-{page_idx+1}' if page_images else None,
                        }
                        if algorithm_record:
                            record['algorithm_id'] = algorithm_record['id']
                        if (kind == 'display' or flags) and valid_bbox(bbox):
                            if group_id not in regions:
                                region = f'regions/{group_id}-math.png'
                                save_region(page, bbox, md.parent/region)
                                regions[group_id] = region
                            record['source_crop'] = regions[group_id]
                        formulas.append(record)
            finally:
                page.close()
    finally:
        document.close()
    text = original
    for start, end, replacement in sorted(replacements, reverse=True):
        text = text[:start] + replacement + text[end:]
    text += '\n\n---\n\n[Formula and algorithm review](review.md)'
    if page_images:
        text += ' · [Original PDF pages](page_index.md)'
    md.write_text(text + '\n', encoding='utf-8')
    summary = {
        'review_version': REVIEW_VERSION, 'source_pdf': str(pdf), 'algorithm_text_policy': algorithm_text,
        'algorithm_count': len(algorithms),
        'native_algorithm_count': sum(a['text_source'] == 'native_pdf' for a in algorithms),
        'unmapped_algorithm_count': sum(not a['markdown_replaced'] for a in algorithms),
        'formula_count': len(formulas), 'display_formula_count': sum(f['kind']=='display' for f in formulas),
        'flagged_formula_count': sum(bool(f['flags']) for f in formulas),
        'source_region_count': len(regions),
        'semantic_accuracy': 'unverified',
        'caveat': 'Heuristics find candidates, not all errors. Native text is not a lossless math representation.',
    }
    report = {'summary': summary, 'algorithms': algorithms, 'formulas': formulas}
    md.with_name('review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    write_review(md.with_name('review.md'), report, page_images=page_images)
    return summary


def write_review(path, report, *, page_images):
    summary = report['summary']
    lines = ['# Formula and algorithm review', '',
             f'Detected formulas: {summary["formula_count"]}; flagged candidates: {summary["flagged_formula_count"]}.',
             f'Algorithms: {summary["algorithm_count"]}; native PDF transcriptions used: {summary["native_algorithm_count"]}.', '',
             'All formula transcriptions remain semantically unverified. No flags does not mean correct.',
             'The inventory covers formulas detected by MinerU; missed detections can still exist.',
             'Inline formula boxes refer to the containing block, not an exact formula crop.', '',
             '[Machine-readable inventory](review.json) · [Unmodified parser Markdown](markdown.raw.md)', '']
    if page_images:
        lines += ['[Original PDF page index](page_index.md)', '']
    for algorithm in report['algorithms']:
        lines += [f'## {algorithm["id"]}', '', f'PDF page {algorithm["page_number"]}; text source: {algorithm["text_source"]}.', '',
                  algorithm['caveat'], '']
        if algorithm.get('source_crop'):
            lines += [f'![Original algorithm]({algorithm["source_crop"]})', '']
        if algorithm['native_rejection_reasons']:
            lines += ['Native extraction notes: ' + ', '.join(algorithm['native_rejection_reasons']), '']
        if not algorithm['markdown_replaced']:
            lines += ['WARNING: block could not be mapped to Markdown; the original transcription was retained.', '']
        lines += ['### Native PDF text', '', code_fence(algorithm['native_text'] or '[No reliable native text]'), '',
                  '### Original OCR transcription', '', code_fence(algorithm['ocr_text'], 'markdown'), '']
    for formula in report['formulas']:
        if formula['kind'] != 'display' and not formula['flags']:
            continue
        lines += [f'## {formula["id"]}', '',
                  f'PDF page {formula["page_number"]}; {formula["kind"]}; region: {formula["bbox_scope"]}.', '',
                  'Review flags: ' + (', '.join(formula['flags']) or 'none; still unverified'), '',
                  code_fence(formula['latex'], 'latex'), '']
        if formula.get('source_crop'):
            lines += [f'![Original formula context]({formula["source_crop"]})', '']
    path.write_text('\n'.join(lines), encoding='utf-8')
