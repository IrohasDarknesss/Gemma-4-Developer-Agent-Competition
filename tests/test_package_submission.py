import shutil
import tempfile
import unittest
from pathlib import Path
import zipfile

from tools.package_submission import build, validate

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'submission'
        shutil.copytree(ROOT / 'submission', self.source)

    def change(self, old, new):
        path = self.source / 'agent.yaml'
        path.write_text(path.read_text().replace(old, new))

    def test_archive_is_reproducible_and_includes_prompt(self):
        first, second = self.base / 'a.zip', self.base / 'b.zip'
        build(self.source, first)
        build(self.source, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            self.assertEqual(set(archive.namelist()), {'agent.yaml', 'prompts/system.md'})
            self.assertIn(b'submit_patch', archive.read('prompts/system.md'))
            self.assertIsNone(archive.testzip())

    def test_rejects_path_traversal(self):
        self.change('prompts/system.md', '../private.md')
        with self.assertRaisesRegex(ValueError, 'Unsafe include'):
            validate(self.source)

    def test_rejects_symlinks(self):
        path = self.source / 'prompts/system.md'
        path.unlink()
        path.symlink_to(ROOT / 'README.md')
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            validate(self.source)

    def test_rejects_unsupported_model(self):
        self.change('gemma-4-e4b-it-qat-w4a16-ct', 'other-model')
        with self.assertRaisesRegex(ValueError, 'Unsupported Gemma'):
            validate(self.source)

    def test_requires_patch_submission_tool(self):
        self.change('  - submit_patch\n', '')
        with self.assertRaisesRegex(ValueError, 'submit_patch'):
            validate(self.source)

    def test_rejects_unapproved_tool(self):
        self.change('- run_command', '- arbitrary_python')
        with self.assertRaisesRegex(ValueError, 'Unsupported baseline tool'):
            validate(self.source)

    def test_rejects_accidental_extra_files(self):
        (self.source / '.env').write_text('example')
        with self.assertRaisesRegex(ValueError, 'only agent.yaml'):
            validate(self.source)

    def test_rejects_output_inside_source(self):
        with self.assertRaisesRegex(ValueError, 'outside submission'):
            build(self.source, self.source / 'submission.zip')

    def test_rejects_legacy_tool_mapping(self):
        self.change('- run_command', '- name: run_command')
        with self.assertRaisesRegex(ValueError, 'Unsupported baseline tool'):
            validate(self.source)

    def test_rejects_include_depth_over_ten(self):
        self.change('prompts/system.md', 'level0.yaml')
        for index in range(11):
            (self.source / f'level{index}.yaml').write_text(
                f'!include level{index + 1}.yaml')
        (self.source / 'level11.yaml').write_text('end')
        with self.assertRaisesRegex(ValueError, 'depth exceeds 10'):
            validate(self.source)

    def test_rejects_cyclic_include(self):
        self.change('prompts/system.md', 'agent.yaml')
        with self.assertRaisesRegex(ValueError, 'Cyclic include'):
            validate(self.source)


if __name__ == '__main__':
    unittest.main()
