import json
import os
from unittest import TestCase

from deepdiff import DeepDiff

from pyaml import Parser

parser = Parser()
folder = "tests/1.0/"


class TestOfficialTestCases(TestCase):
    def test_each_test_case(self):
        test_files = sorted(os.listdir(folder))
        for i, f in enumerate(test_files):
            if f.startswith("all"):
                continue
            with open(folder + f, "r") as test_file:
                contents = test_file.read()
                lines = contents.splitlines()
                headers = "\n".join(lines[0:2])
                test_body = "\n".join(lines[2:])
                test_headers = parser.parse(headers)
                with self.subTest(
                    msg=f"{i}/{len(test_files)} Test file: {f}: {test_headers.get('test')}"
                ):
                    expected = json.loads(test_headers.get("result"))
                    result = parser.parse(test_body)
                    self.assertEqual(
                        DeepDiff(result, expected),
                        {},
                        msg=f"\n\nExpected:\n{json.dumps(expected, indent=4)} \n===\nGot:\n{json.dumps(result, indent=4)}",
                    )
