from absl.testing import absltest

import pytest
import sample.main


class SampleTest(absltest.TestCase):
    def test_foo(self):
        if False:
          self.fail('does this work?)')