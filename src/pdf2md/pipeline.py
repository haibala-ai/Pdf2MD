"""PDF-only MinerU conversion with provenance, resumable batches and structural QA.

Word overlap and review heuristics cannot establish lossless PDF conversion.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.parse import unquote, urlsplit
import uuid
import zipfile

from markdown_it import MarkdownIt
from pypdf import PdfReader
from .review import REVIEW_VERSION, enhance

WORKFLOW_VERSION = 3


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def file_hash(path: Path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tokens(text):
    import unicodedata
    text = unicodedata.normalize('NFKC', text).casefold()
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
    return re.findall(r'[a-z][a-z0-9]{2,}', text)


def image_sources(markdown):
    """Handle Markdown reference images, encoded spaces and HTML images."""
    images = []

    class Images(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag.lower() == 'img' and dict(attrs).get('src'):
                images.append(dict(attrs)['src'])

    html = Images()

    def walk(items):
        for item in items:
            if item.type == 'image':
                images.append(item.attrGet('src'))
            if item.type in ('html_inline', 'html_block'):
                html.feed(item.content)
            if item.children:
                walk(item.children)

    walk(MarkdownIt('commonmark', {'html': True}).parse(markdown))
    return images


def quality(pdf: Path, md: Path):
    reader = PdfReader(pdf)
    page_text = [page.extract_text(extraction_mode='plain') or '' for page in reader.pages]
    text = md.read_text(encoding='utf-8')
    source_text = '\n'.join(page_text)
    src, dst = Counter(tokens(source_text)), Counter(tokens(text))
    english_count = sum(src.values())
    cjk_count = len(re.findall(r'[\u3400-\u9fff]', source_text))
    applicable = english_count >= 100 and cjk_count <= english_count
    coverage = round(sum((src & dst).values()) / english_count, 4) if applicable else None
    warnings = []
    if not applicable:
        warnings.append('English coverage not applicable: scanned, short or non-English PDF; review OCR manually.')
    images = image_sources(text)
    review_images = []
    for companion in ('review.md', 'page_index.md'):
        if md.with_name(companion).exists():
            review_images.extend(image_sources(md.with_name(companion).read_text(encoding='utf-8')))
    missing = []
    for image in dict.fromkeys(images + review_images):
        parsed = urlsplit(image)
        if parsed.scheme or parsed.netloc:
            continue
        path = (md.parent / unquote(parsed.path)).resolve()
        if not path.is_relative_to(md.parent.resolve()) or not path.is_file():
            missing.append(image)
    middle = json.loads(md.with_name('middle_json.json').read_text(encoding='utf-8'))
    structured = json.loads(md.with_name('structured_content.json').read_text(encoding='utf-8'))
    expected = list(range(len(reader.pages)))
    indices = [page.get('page_idx') for page in middle.get('pages', [])]
    structured_indices = [page.get('page_idx') for page in structured.get('pages', [])]
    all_pages = indices == expected and structured_indices == expected
    full_document = middle.get('is_full_document') is True and structured.get('is_full_document') is True
    empty_pages = [page.get('page_idx') for page in structured.get('pages', []) if not page.get('blocks')]
    if empty_pages:
        warnings.append(f'Pages with no structured blocks (possibly blank): {empty_pages}')
    review = {}
    if md.with_name('review.json').exists():
        review = json.loads(md.with_name('review.json').read_text(encoding='utf-8'))['summary']
        if review['formula_count'] or review['algorithm_count']:
            warnings.append('Formula semantics and algorithm layout remain unverified; compare review.md with PDF evidence.')
        if review['flagged_formula_count']:
            warnings.append(f"Formula review candidates: {review['flagged_formula_count']}")
        if review['unmapped_algorithm_count']:
            warnings.append(f"Unmapped algorithm blocks retained: {review['unmapped_algorithm_count']}")
    checks = {
        'nonempty_markdown': bool(text.strip()), 'all_pages_present': all_pages,
        'full_document_flags': full_document, 'local_images_present': not missing,
        'english_word_coverage': coverage >= .80 if applicable else None,
    }
    passed = all(value is not False for value in checks.values())
    return {
        'source_pdf': str(pdf), 'markdown': str(md),
        'pdf_pages': len(reader.pages), 'parsed_pages': len(indices),
        'parsed_page_indices_zero_based': indices,
        'structured_page_indices_zero_based': structured_indices,
        'is_full_document': full_document, 'all_pages_present': all_pages,
        'markdown_chars': len(text), 'markdown_lines': len(text.splitlines()),
        'heading_count': len(re.findall(r'^#{1,6}\s+', text, re.M)),
        'image_references': len(images), 'missing_local_images': missing,
        'evidence_image_references': len(review_images), 'pdf_review': review,
        'html_table_count': len(re.findall(r'<table\b', text, re.I)),
        'replacement_character_count': text.count('\ufffd'),
        'source_word_occurrence_coverage': coverage,
        'word_coverage_applicable': applicable, 'source_english_word_count': english_count,
        'empty_structured_pages_zero_based': empty_pages,
        'coverage_caveat': 'Structural checks and word overlap do not establish formula accuracy, reading order or losslessness.',
        'checks': checks, 'warnings': warnings,
        'quality_status': 'failed' if not passed else ('needs_review' if warnings else 'passed'),
        'mechanical_checks_passed': passed,
    }


def safe_extract(archive: Path, target: Path):
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            name = item.filename.replace('\\', '/')
            if (PurePosixPath(name).is_absolute() or PureWindowsPath(name).drive
                    or '..' in PurePosixPath(name).parts or ':' in name
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError(f'Unsafe ZIP member: {item.filename}')
            if not (target / name).resolve().is_relative_to(target.resolve()):
                raise ValueError(f'ZIP member outside output: {item.filename}')
        bundle.extractall(target)


def find_markdown(directory: Path):
    candidates = sorted(directory.rglob('markdown.md'))
    if len(candidates) != 1:
        raise ValueError(f'Expected one markdown.md in the new archive, found {len(candidates)}')
    for name in ('middle_json.json', 'structured_content.json'):
        if not candidates[0].with_name(name).is_file():
            raise ValueError(f'MinerU output is missing {name}')
    return candidates[0]


def artifact_hashes(directory: Path):
    return {p.relative_to(directory).as_posix(): file_hash(p)
            for p in sorted(directory.rglob('*')) if p.is_file() and p.name != 'run.json'}


def render_page_evidence(pdf: Path, directory: Path):
    """Optional visual ground truth; it does not replace editable Markdown text."""
    import pypdfium2 as pdfium
    images = directory / 'pages'
    images.mkdir()
    index = ['# Original PDF page evidence', '',
             'Use these rendered pages to check formulas, algorithms and reading order.', '']
    document = pdfium.PdfDocument(pdf)
    try:
        for number in range(len(document)):
            page = document[number]
            bitmap = page.render(scale=1.5)
            try:
                filename = f'page-{number + 1:04d}.png'
                bitmap.to_pil().save(images / filename)
            finally:
                bitmap.close()
                page.close()
            index += [f'## Page {number + 1}', '', f'![Page {number + 1}](pages/{filename})', '']
    finally:
        document.close()
    (directory / 'page_index.md').write_text('\n'.join(index), encoding='utf-8')


def reusable(target: Path, fingerprint: dict):
    try:
        record = json.loads((target / 'run.json').read_text(encoding='utf-8'))
        if record.get('status') != 'success' or record.get('fingerprint') != fingerprint:
            return None
        artifacts = record.get('artifact_sha256', {})
        if not artifacts or any(not (target / name).is_file() or file_hash(target / name) != digest
                                for name, digest in artifacts.items()):
            return None
        return record
    except (OSError, ValueError):
        return None


def document_id(pdf: Path, output_root: Path, tier: str, digest: str):
    # All tiers in one document folder must refer to the same source PDF.
    for record_path in (output_root / pdf.stem).glob('*/run.json'):
        try:
            record = json.loads(record_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            # A damaged manifest invalidates the cache; preserve old output as history.
            continue
        previous = record.get('pdf_sha256')
        if previous and previous != digest:
            return f'{pdf.stem}-{digest[:12]}'
    return pdf.stem


def publish(staging: Path, target: Path, output_root: Path, attempt: str):
    """Keep previous results as history; never mix stale and newly parsed files."""
    root = output_root.resolve()
    if not staging.resolve().is_relative_to(root) or not target.resolve().is_relative_to(root):
        raise ValueError('Publish paths must stay inside the output directory')
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if target.exists():
        previous = root / '_history' / target.parent.name / f'{target.name}-{attempt}'
        previous.parent.mkdir(parents=True, exist_ok=True)
        target.rename(previous)
    try:
        staging.rename(target)
    except OSError:
        if previous is not None:
            previous.rename(target)
        raise


def convert(pdf: Path, tier: str, output_root: Path | None = None, *, force=False,
            keep_archive=False, page_images=True, algorithm_text='native', ocr_mode='auto', timeout=None):
    pdf = pdf.resolve()
    output_root = (output_root or Path.cwd() / 'output').resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    digest = file_hash(pdf)
    name = document_id(pdf, output_root, tier, digest)
    target = output_root / name / tier
    environment = os.environ.copy()
    environment.setdefault('MINERU_HOME', str(Path.cwd() / '.mineru'))
    environment.setdefault('MINERU_MODEL_SOURCE', 'auto')
    environment.setdefault('MINERU_PROCESSING_WINDOW_SIZE', '3')
    # Keep the distribution on the tested CPU/ONNX path, even if Torch or a GPU
    # was independently installed on the recipient's machine.
    environment['MINERU_MODEL_SMALL_BACKEND'] = 'onnx'
    environment['MINERU_DEVICE_MODE'] = 'cpu'
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONIOENCODING'] = 'utf-8'
    fingerprint = {
        'workflow_version': WORKFLOW_VERSION, 'pdf_sha256': digest,
        'review_version': REVIEW_VERSION, 'algorithm_text': algorithm_text, 'ocr_mode': ocr_mode,
        'mineru_version': importlib.metadata.version('mineru'), 'tier': tier,
        'pages': 'all', 'keep_archive': keep_archive, 'page_images': page_images,
        'model_source': environment['MINERU_MODEL_SOURCE'],
        'processing_window_size': environment['MINERU_PROCESSING_WINDOW_SIZE'],
        'small_backend': 'onnx', 'device': 'cpu',
    }
    cached = reusable(target, fingerprint) if not force else None
    if cached:
        cached_quality = json.loads((target / 'quality.json').read_text(encoding='utf-8'))
        return {'pdf': str(pdf), 'status': 'skipped', 'target': str(target),
                'markdown': cached['markdown'], 'mechanical_checks_passed': True,
                'quality_status': cached_quality['quality_status'], 'pdf_review': cached.get('pdf_review', {})}
    executable = Path(sys.executable).parent / ('mineru-kit.exe' if os.name == 'nt' else 'mineru-kit')
    if not executable.is_file():
        raise RuntimeError(f'MinerU CLI is missing: {executable}. Run scripts/setup.sh or scripts/setup.ps1 first.')
    attempt = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    log = output_root / '_logs' / f'{name}_{tier}_{attempt}.log'
    log.parent.mkdir(exist_ok=True)
    record = {
        'attempt': attempt, 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'pdf': str(pdf), 'pdf_sha256': digest, 'tier': tier,
        'mineru_version': fingerprint['mineru_version'], 'fingerprint': fingerprint,
        'log': str(log), 'status': 'running',
    }
    attempt_file = output_root / '_runs' / f'{name}_{tier}_{attempt}.json'
    write_json(attempt_file, record)
    started = time.perf_counter()
    try:
        if not PdfReader(pdf).pages:
            raise ValueError('PDF contains no pages')
        with tempfile.TemporaryDirectory(prefix='.parse-', dir=output_root) as temp:
            staging = Path(temp) / 'result'
            staging.mkdir()
            archive = staging / 'result.zip'
            command = [str(executable), 'parse', str(pdf), '--tier', tier, '--pages', 'all',
                       '--ocr-mode', ocr_mode, '--format', 'zip', '-o', str(archive)]
            record['command'] = command
            print(f'Converting {pdf.name} [{tier}]; log: {log}', flush=True)
            with log.open('w', encoding='utf-8') as stream:
                proc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                      env=environment, timeout=timeout)
            record['exit_code'] = proc.returncode
            if proc.returncode:
                raise RuntimeError(f'MinerU exited {proc.returncode}; see {log}')
            safe_extract(archive, staging)
            md = find_markdown(staging)
            review = enhance(pdf, md, page_images=page_images, algorithm_text=algorithm_text)
            if page_images:
                render_page_evidence(pdf, md.parent)
            report = quality(pdf, md)
            report['markdown'] = str(target / md.relative_to(staging))
            write_json(staging / 'quality.json', report)
            if not keep_archive:
                archive.unlink()
            record.update({
                'status': 'success' if report['mechanical_checks_passed'] else 'quality_failed',
                'markdown': report['markdown'], 'quality_file': str(target / 'quality.json'),
                'elapsed_seconds': round(time.perf_counter() - started, 3),
                'artifact_sha256': artifact_hashes(staging),
                'pdf_review': review,
            })
            write_json(staging / 'run.json', record)
            publish(staging, target, output_root, attempt)
        write_json(attempt_file, record)
        result = {'pdf': str(pdf), 'status': record['status'], 'target': str(target),
                  'markdown': record['markdown'], 'pages': report['pdf_pages'],
                  'seconds': record['elapsed_seconds'], 'word_coverage': report['source_word_occurrence_coverage'],
                  'quality_status': report['quality_status'],
                  'pdf_review': review,
                  'mechanical_checks_passed': report['mechanical_checks_passed']}
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return result
    except Exception as exc:
        record.update({'status': 'failed', 'error': str(exc),
                       'elapsed_seconds': round(time.perf_counter() - started, 3)})
        with log.open('a', encoding='utf-8') as stream:
            stream.write('\n' + traceback.format_exc())
        write_json(attempt_file, record)
        raise


def discover(source: Path, recursive=False):
    source = source.resolve()
    if source.is_dir():
        candidates = source.rglob('*') if recursive else source.iterdir()
        pdfs = sorted(p for p in candidates if p.is_file() and p.suffix.casefold() == '.pdf')
    else:
        pdfs = [source] if source.is_file() and source.suffix.casefold() == '.pdf' else []
    if not pdfs:
        raise ValueError(f'No PDFs found: {source}')
    return pdfs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Local PDF or directory')
    parser.add_argument('--tier', choices=['flash', 'basic'], default='basic')
    parser.add_argument('--output-dir', type=Path, default=Path.cwd() / 'output')
    parser.add_argument('--recursive', action='store_true', help='Include PDF subdirectories')
    parser.add_argument('--force', action='store_true', help='Reparse; retain old output under _history')
    parser.add_argument('--keep-archive', action='store_true', help='Also retain raw result.zip')
    evidence = parser.add_mutually_exclusive_group()
    evidence.add_argument('--page-images', dest='page_images', action='store_true', default=True, help='Save original page images (default)')
    evidence.add_argument('--no-page-images', dest='page_images', action='store_false', help='Omit full-page images; algorithm/math review crops remain')
    parser.add_argument('--algorithm-text', choices=['native','ocr'], default='native', help='Prefer verified native algorithm text, or retain OCR')
    parser.add_argument('--ocr-mode', choices=['auto','txt','ocr'], default='auto', help='MinerU PDF text/OCR mode; auto is recommended')
    parser.add_argument('--timeout', type=float, default=None, help='Maximum seconds per MinerU process')
    args = parser.parse_args(argv)
    if args.timeout is not None and args.timeout <= 0:
        parser.error('--timeout must be positive')
    try:
        pdfs = discover(args.input, args.recursive)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for pdf in pdfs:
        try:
            results.append(convert(pdf, args.tier, output, force=args.force,
                                   keep_archive=args.keep_archive, page_images=args.page_images,
                                   algorithm_text=args.algorithm_text, ocr_mode=args.ocr_mode, timeout=args.timeout))
        except Exception as exc:
            print(f'FAILED {pdf}: {exc}', file=sys.stderr, flush=True)
            results.append({'pdf': str(pdf), 'status': 'failed', 'error': str(exc)})
    summary = {
        'finished_at_utc': datetime.now(timezone.utc).isoformat(), 'tier': args.tier,
        'counts': dict(Counter(item['status'] for item in results)), 'results': results,
    }
    batch = output / '_runs' / ('batch-' + uuid.uuid4().hex[:12] + '.json')
    write_json(batch, summary)
    write_json(output / 'batch_summary.json', summary)
    print(f'Batch summary: {batch}', flush=True)
    if any(item['status'] == 'failed' for item in results):
        return 1
    return 2 if any(item['status'] == 'quality_failed' for item in results) else 0


if __name__ == '__main__':
    raise SystemExit(main())
