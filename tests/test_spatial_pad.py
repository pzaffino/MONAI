# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import unittest

from parameterized import parameterized

from monai.transforms import SpatialPad
from tests.padders import PadTest

TESTS = []
TESTS.append([{"spatial_size": [3, 4], "method": "end"}, (1, 2, 3), (1, 3, 4)])
TESTS.append([{"spatial_size": [15, 4, -1], "method": "symmetric"}, (3, 8, 8, 4), (3, 15, 8, 4)])


class TestSpatialPad(PadTest):
    Padder = SpatialPad

    @parameterized.expand(TESTS)
    def test_pad(self, input_param, input_shape, expected_shape):
        self.pad_test(input_param, input_shape, expected_shape)

    def test_pad_kwargs(self):
        kwargs = {"spatial_size": [15, 8], "method": "end", "mode": "constant"}
        unchanged_slices = [slice(None), slice(None, 8), slice(None, 4)]
        self.pad_test_kwargs(unchanged_slices, **kwargs)


if __name__ == "__main__":
    unittest.main()
