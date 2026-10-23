"""Regression checks for damaged inputs, stale outputs and misleading QA."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from pdf2md import pipeline as workflow


def pdf_file(path, text=''):
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=600)
    if text:
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(('BT /F1 10 Tf 20 550 Td (' + text + ') Tj ET').encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as output:
        writer.write(output)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf, self.md = self.root/'paper.pdf', self.root/'markdown.md'
        self.body = 'alpha beta gamma delta experiment results ' * 25
        pdf_file(self.pdf, self.body)
        self.md.write_text(self.body, encoding='utf-8')
        self.output = {'pages': [{'page_idx': 0, 'blocks': [{'type': 'text', 'content': self.body}]}],
                       'is_full_document': True}
        self.save_json()

    def save_json(self):
        for name in ('middle_json.json', 'structured_content.json'):
            workflow.write_json(self.root/name, self.output)

    def test_generic_paper_without_pipnn_anchors_passes(self):
        result = workflow.quality(self.pdf, self.md)
        self.assertTrue(result['mechanical_checks_passed'])
        self.assertEqual(result['source_word_occurrence_coverage'], 1.0)
        self.assertNotIn('sample_anchor_checks', result)

    def test_missing_half_the_native_text_fails(self):
        self.md.write_text(self.body[:len(self.body)//2], encoding='utf-8')
        self.assertFalse(workflow.quality(self.pdf, self.md)['mechanical_checks_passed'])

    def test_scan_has_no_english_ground_truth_and_needs_review(self):
        pdf_file(self.pdf)
        result = workflow.quality(self.pdf, self.md)
        self.assertIsNone(result['source_word_occurrence_coverage'])
        self.assertTrue(result['mechanical_checks_passed'])
        self.assertEqual(result['quality_status'], 'needs_review')

    def test_chinese_text_is_not_failed_for_english_coverage(self):
        class Page:
            def extract_text(self, **kwargs):
                return '中文论文公式表格摘要内容' * 30
        with patch.object(workflow, 'PdfReader') as reader:
            reader.return_value.pages = [Page()]
            self.assertIsNone(workflow.quality(self.pdf, self.md)['checks']['english_word_coverage'])

    def test_truncated_or_duplicate_pages_fail(self):
        for pages in ([], [self.output['pages'][0]] * 2):
            with self.subTest(pages=len(pages)):
                self.output['pages'] = pages
                self.save_json()
                self.assertFalse(workflow.quality(self.pdf, self.md)['all_pages_present'])

    def test_full_document_flag_is_required(self):
        self.output['is_full_document'] = False
        self.save_json()
        self.assertFalse(workflow.quality(self.pdf, self.md)['mechanical_checks_passed'])

    def test_encoded_reference_and_html_images_are_checked(self):
        image = self.root/'image with spaces.png'
        image.write_bytes(b'image')
        self.md.write_text(self.body+'\n![figure][id]\n\n[id]: <image with spaces.png>\n<img src="missing.png">', encoding='utf-8')
        result = workflow.quality(self.pdf, self.md)
        self.assertEqual(result['image_references'], 2)
        self.assertEqual(result['missing_local_images'], ['missing.png'])
        self.assertFalse(result['mechanical_checks_passed'])


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_recursive_and_uppercase_pdf_discovery(self):
        (self.root/'nested').mkdir()
        for name in ['one.PDF', 'nested/two.pdf', 'other.txt']:
            (self.root/name).write_bytes(b'file')
        self.assertEqual(len(workflow.discover(self.root)), 1)
        self.assertEqual(len(workflow.discover(self.root, True)), 2)

    def test_different_same_name_pdfs_do_not_share_output(self):
        workflow.write_json(self.root/'paper'/'basic'/'run.json', {'pdf_sha256': 'first'})
        self.assertEqual(workflow.document_id(Path('paper.pdf'), self.root, 'basic', 'first'), 'paper')
        self.assertEqual(workflow.document_id(Path('paper.pdf'), self.root, 'basic', 'second'), 'paper-second')
        self.assertEqual(workflow.document_id(Path('paper.pdf'), self.root, 'flash', 'second'), 'paper-second')

    def test_resume_rejects_modified_artifact(self):
        target = self.root/'result'
        target.mkdir()
        (target/'markdown.md').write_text('original')
        workflow.write_json(target/'run.json', {'status': 'success', 'fingerprint': {'source': 'abc'},
                            'artifact_sha256': workflow.artifact_hashes(target)})
        self.assertIsNotNone(workflow.reusable(target, {'source': 'abc'}))
        (target/'markdown.md').write_text('corrupted')
        self.assertIsNone(workflow.reusable(target, {'source': 'abc'}))

    def test_archive_cannot_write_outside_attempt(self):
        for name in ['../escape.md', '/absolute.md', 'C:/escape.md', '..\\escape.md']:
            with self.subTest(name=name):
                archive = self.root/'result.zip'
                with zipfile.ZipFile(archive, 'w') as bundle:
                    bundle.writestr(name, 'bad')
                with self.assertRaises(ValueError):
                    workflow.safe_extract(archive, self.root/'unpack')
        self.assertFalse((self.root/'escape.md').exists())

    def test_reparse_preserves_previous_output(self):
        old = self.root/'paper'/'basic'
        old.mkdir(parents=True)
        (old/'stale.md').write_text('old')
        stage = self.root/'staging'
        stage.mkdir()
        (stage/'markdown.md').write_text('new')
        workflow.publish(stage, old, self.root, 'attempt')
        self.assertEqual((old/'markdown.md').read_text(), 'new')
        self.assertFalse((old/'stale.md').exists())
        self.assertEqual((self.root/'_history/paper/basic-attempt/stale.md').read_text(), 'old')

    def test_one_failure_does_not_abort_rest_of_batch(self):
        inputs = self.root/'input'
        inputs.mkdir()
        for name in ['a.pdf', 'b.pdf']:
            (inputs/name).write_bytes(b'fixture')
        with patch.object(workflow, 'convert', side_effect=[ValueError('damaged PDF'), {'status': 'success'}]) as convert:
            code = workflow.main(['--input', str(inputs), '--output-dir', str(self.root/'output')])
        self.assertEqual(code, 1)
        self.assertEqual(convert.call_count, 2)
        summary = json.loads((self.root/'output/batch_summary.json').read_text())
        self.assertEqual(summary['counts'], {'failed': 1, 'success': 1})


if __name__ == '__main__':
    unittest.main()
