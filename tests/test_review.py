"""Evidence-based algorithm fallback and formula audits must not invent math."""
from pathlib import Path
import json
import tempfile
import unittest

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from pdf2md import review as pdf_review
from pdf2md import pipeline as workflow


BODY = 'Algorithm 1: Example\nInput: a collection of candidate points\nOutput: the nearest point\n1 for every candidate do\n2 if alpha < beta then\n3 return the nearest point'
OCR = BODY.replace('if alpha', '$\\inf_{\\cdot} \\alpha$')


def algorithm_pdf(path, body=BODY):
    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=600)
    font = DictionaryObject({NameObject('/Type'):NameObject('/Font'), NameObject('/Subtype'):NameObject('/Type1'), NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    stream = DecodedStreamObject()
    pieces = ['BT /F1 10 Tf 30 550 Td']
    for index, line in enumerate(body.splitlines()):
        if index:
            pieces.append('0 -15 Td')
        pieces.append('('+line+') Tj')
    pieces.append('ET')
    stream.set_data('\n'.join(pieces).encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as output:
        writer.write(output)


class NativeDecisionTests(unittest.TestCase):
    def test_verified_keywords_can_replace_ocr_inf_without_rewriting_math(self):
        accepted, reasons, _ = pdf_review.native_algorithm_decision(BODY, OCR)
        self.assertTrue(accepted)
        self.assertEqual(reasons, [])

    def test_scan_wrong_title_missing_step_and_bad_encoding_reject_native(self):
        for native in ('', BODY.replace('Example','Different'), BODY.replace('2 if alpha < beta then\n',''), BODY+'\ufffd'):
            with self.subTest(native=native[-30:]):
                self.assertFalse(pdf_review.native_algorithm_decision(native,OCR)[0])

    def test_html_mapping_normalizes_text_escapes_but_preserves_latex(self):
        self.assertEqual(pdf_review.canonical_algorithm(r'Prune\\_edges $x\_y$ &lt; z'),
                         pdf_review.canonical_algorithm(r'Prune_edges $x\_y$ < z'))
        self.assertNotEqual(pdf_review.canonical_algorithm(r'$x\_y$'),pdf_review.canonical_algorithm(r'$x_y$'))

    def test_legitimate_infimum_and_escaped_braces_are_not_changed(self):
        latex=r'\inf_{x \in \{0,1\}} f(x)'
        self.assertEqual(pdf_review.latex_flags(latex), [])
        self.assertEqual(latex,r'\inf_{x \in \{0,1\}} f(x)')

    def test_formula_queue_detects_syntax_and_algorithm_conflicts(self):
        self.assertIn('unbalanced_braces',pdf_review.latex_flags(r'x_{a'))
        self.assertIn('mismatched_environment',pdf_review.latex_flags(r'\begin{matrix}x\end{aligned}'))
        self.assertIn('possible_if_read_as_inf',pdf_review.latex_flags(r'\inf_{\cdot} x',algorithm=True,context='6 if x then'))
        self.assertEqual(pdf_review.latex_flags(r'\inf x',algorithm=True,context='return infimum'),[])


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.pdf=self.root/'paper.pdf'
        self.md=self.root/'markdown.md'
        algorithm_pdf(self.pdf)
        self.raw='<div class="docvortex-algorithm" style="white-space: pre-wrap;">\n'+OCR+'\n</div>\n'
        self.md.write_text(self.raw,encoding='utf-8')
        bbox=[.05,.05,.95,.95]
        middle={'pages':[{'page_idx':0,'blocks':[{'type':'code','sub_type':'algorithm','bbox':bbox,'content':[{'type':'algorithm_body','content':[{'type':'equation_inline','content':r'\inf_{\cdot} \alpha'}]}]}]}],'is_full_document':True}
        structured={'pages':[{'page_idx':0,'blocks':[{'type':'code','sub_type':'algorithm','bbox':bbox,'content':OCR}]}],'is_full_document':True}
        workflow.write_json(self.root/'middle_json.json',middle)
        workflow.write_json(self.root/'structured_content.json',structured)

    def test_native_transcription_has_original_crop_raw_evidence_and_review_flags(self):
        before=workflow.file_hash(self.root/'middle_json.json')
        result=pdf_review.enhance(self.pdf,self.md,page_images=False)
        final=self.md.read_text(encoding='utf-8')
        self.assertIn('2 if alpha < beta then',final)
        self.assertNotIn(r'\inf',final)
        self.assertEqual((self.root/'markdown.raw.md').read_text(encoding='utf-8'),self.raw)
        self.assertEqual(before,workflow.file_hash(self.root/'middle_json.json'))
        self.assertEqual(result['native_algorithm_count'],1)
        self.assertEqual(result['flagged_formula_count'],1)
        self.assertTrue(list((self.root/'regions').glob('*.png')))
        self.assertFalse(workflow.quality(self.pdf,self.md)['missing_local_images'])
        self.assertEqual(workflow.quality(self.pdf,self.md)['quality_status'],'needs_review')

    def test_reprocessing_is_idempotent(self):
        pdf_review.enhance(self.pdf,self.md,page_images=False)
        first=self.md.read_bytes()
        pdf_review.enhance(self.pdf,self.md,page_images=False)
        self.assertEqual(first,self.md.read_bytes())

    def test_forced_ocr_and_unmapped_blocks_preserve_original_text(self):
        result=pdf_review.enhance(self.pdf,self.md,page_images=False,algorithm_text='ocr')
        self.assertEqual(result['native_algorithm_count'],0)
        self.assertIn(r'\inf',self.md.read_text(encoding='utf-8'))
        (self.root/'markdown.raw.md').write_text('Unmatched body',encoding='utf-8')
        result=pdf_review.enhance(self.pdf,self.md,page_images=False)
        self.assertEqual(result['unmapped_algorithm_count'],1)
        self.assertIn('Unmatched body',self.md.read_text(encoding='utf-8'))

    def test_missing_review_crop_is_a_mechanical_failure(self):
        pdf_review.enhance(self.pdf,self.md,page_images=False)
        for image in (self.root/'regions').glob('*.png'):
            image.unlink()
        result=workflow.quality(self.pdf,self.md)
        self.assertFalse(result['mechanical_checks_passed'])
        self.assertTrue(result['missing_local_images'])


if __name__=='__main__':
    unittest.main()
