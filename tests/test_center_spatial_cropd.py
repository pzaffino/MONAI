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

import numpy as np
from parameterized import parameterized

from monai.transforms import CenterSpatialCropd
from tests.croppers import CropTest

TEST_SHAPES = [
    [
        {"keys": "img", "roi_size": [2, -1, -1]},
        (3, 3, 3, 3),
        (3, 2, 3, 3),
        (slice(None), slice(None, -1), slice(None), slice(None)),
    ],
    [
        {"keys": "img", "roi_size": [2, 2, 2]},
        (3, 3, 3, 3),
        (3, 2, 2, 2),
        (slice(None), slice(None, -1), slice(None, -1), slice(None, -1)),
    ],
]

TEST_CASES = [
    [
        {"keys": "img", "roi_size": [2, 2]},
        np.array([[[0, 0, 0, 0, 0], [0, 1, 2, 1, 0], [0, 2, 3, 2, 0], [0, 1, 2, 1, 0], [0, 0, 0, 0, 0]]]),
        np.array([[[1, 2], [2, 3]]]),
    ]
]


class TestCenterSpatialCropd(CropTest):
    Cropper = CenterSpatialCropd

    @parameterized.expand(TEST_SHAPES)
    def test_shape(self, input_param, input_shape, expected_shape, same_area):
        self.crop_test(input_param, input_shape, expected_shape, same_area)

    @parameterized.expand(TEST_CASES)
    def test_value(self, input_param, input_data, expected_value):
        self.crop_test_value(input_param, input_data, expected_value)


if __name__ == "__main__":
    unittest.main()
