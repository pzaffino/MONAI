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
"""
A collection of dictionary-based wrappers around the "vanilla" transforms for crop and pad operations
defined in :py:class:`monai.transforms.croppad.array`.

Class names are ended with 'd' to denote dictionary-based transforms.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Mapping, Sequence
from copy import deepcopy
from typing import Any

import numpy as np
import torch

from monai.config import IndexSelection, KeysCollection, SequenceStr
from monai.config.type_definitions import NdarrayOrTensor
from monai.data.meta_tensor import MetaTensor
from monai.transforms.croppad.array import (
    BorderPad,
    BoundingRect,
    CenterScaleCrop,
    CenterSpatialCrop,
    Crop,
    CropForeground,
    DivisiblePad,
    Pad,
    RandCropByLabelClasses,
    RandCropByPosNegLabel,
    RandScaleCrop,
    RandSpatialCrop,
    RandSpatialCropSamples,
    RandWeightedCrop,
    ResizeWithPadOrCrop,
    SpatialCrop,
    SpatialPad,
)
from monai.transforms.inverse import InvertibleTransform
from monai.transforms.transform import MapTransform, Randomizable
from monai.transforms.utils import is_positive
from monai.utils import MAX_SEED, Method, PytorchPadMode, ensure_tuple_rep
from monai.utils.deprecate_utils import deprecated_arg

__all__ = [
    "Padd",
    "SpatialPadd",
    "BorderPadd",
    "DivisiblePadd",
    "Cropd",
    "RandCropd",
    "SpatialCropd",
    "CenterSpatialCropd",
    "CenterScaleCropd",
    "RandScaleCropd",
    "RandSpatialCropd",
    "RandSpatialCropSamplesd",
    "CropForegroundd",
    "RandWeightedCropd",
    "RandCropByPosNegLabeld",
    "ResizeWithPadOrCropd",
    "BoundingRectd",
    "RandCropByLabelClassesd",
    "PadD",
    "PadDict",
    "SpatialPadD",
    "SpatialPadDict",
    "BorderPadD",
    "BorderPadDict",
    "DivisiblePadD",
    "DivisiblePadDict",
    "CropD",
    "CropDict",
    "RandCropD",
    "RandCropDict",
    "SpatialCropD",
    "SpatialCropDict",
    "CenterSpatialCropD",
    "CenterSpatialCropDict",
    "CenterScaleCropD",
    "CenterScaleCropDict",
    "RandScaleCropD",
    "RandScaleCropDict",
    "RandSpatialCropD",
    "RandSpatialCropDict",
    "RandSpatialCropSamplesD",
    "RandSpatialCropSamplesDict",
    "CropForegroundD",
    "CropForegroundDict",
    "RandWeightedCropD",
    "RandWeightedCropDict",
    "RandCropByPosNegLabelD",
    "RandCropByPosNegLabelDict",
    "ResizeWithPadOrCropD",
    "ResizeWithPadOrCropDict",
    "BoundingRectD",
    "BoundingRectDict",
    "RandCropByLabelClassesD",
    "RandCropByLabelClassesDict",
]


class Padd(MapTransform, InvertibleTransform):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.Pad`.

    """

    backend = Pad.backend

    def __init__(
        self,
        keys: KeysCollection,
        padder: Pad,
        mode: SequenceStr = PytorchPadMode.CONSTANT,
        allow_missing_keys: bool = False,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            padder: pad transform for the input image.
            mode: available modes for numpy array:{``"constant"``, ``"edge"``, ``"linear_ramp"``, ``"maximum"``,
                ``"mean"``, ``"median"``, ``"minimum"``, ``"reflect"``, ``"symmetric"``, ``"wrap"``, ``"empty"``}
                available modes for PyTorch Tensor: {``"constant"``, ``"reflect"``, ``"replicate"``, ``"circular"``}.
                One of the listed string values or a user supplied function. Defaults to ``"constant"``.
                See also: https://numpy.org/doc/1.18/reference/generated/numpy.pad.html
                https://pytorch.org/docs/stable/generated/torch.nn.functional.pad.html
                It also can be a sequence of string, each element corresponds to a key in ``keys``.
            allow_missing_keys: don't raise exception if key is missing.

        """
        super().__init__(keys, allow_missing_keys)
        self.padder = padder
        self.mode = ensure_tuple_rep(mode, len(self.keys))

    def __call__(self, data: Mapping[Hashable, torch.Tensor]) -> dict[Hashable, torch.Tensor]:
        d = dict(data)
        for key, m in self.key_iterator(d, self.mode):
            d[key] = self.padder(d[key], mode=m)
        return d

    def inverse(self, data: Mapping[Hashable, MetaTensor]) -> dict[Hashable, MetaTensor]:
        d = dict(data)
        for key in self.key_iterator(d):
            d[key] = self.padder.inverse(d[key])
        return d


class SpatialPadd(Padd):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.SpatialPad`.
    Performs padding to the data, symmetric for all sides or all on one side for each dimension.

    """

    def __init__(
        self,
        keys: KeysCollection,
        spatial_size: Sequence[int] | int,
        method: str = Method.SYMMETRIC,
        mode: SequenceStr = PytorchPadMode.CONSTANT,
        allow_missing_keys: bool = False,
        **kwargs,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            spatial_size: the spatial size of output data after padding, if a dimension of the input
                data size is larger than the pad size, will not pad that dimension.
                If its components have non-positive values, the corresponding size of input image will be used.
                for example: if the spatial size of input data is [30, 30, 30] and `spatial_size=[32, 25, -1]`,
                the spatial size of output data will be [32, 30, 30].
            method: {``"symmetric"``, ``"end"``}
                Pad image symmetrically on every side or only pad at the end sides. Defaults to ``"symmetric"``.
            mode: available modes for numpy array:{``"constant"``, ``"edge"``, ``"linear_ramp"``, ``"maximum"``,
                ``"mean"``, ``"median"``, ``"minimum"``, ``"reflect"``, ``"symmetric"``, ``"wrap"``, ``"empty"``}
                available modes for PyTorch Tensor: {``"constant"``, ``"reflect"``, ``"replicate"``, ``"circular"``}.
                One of the listed string values or a user supplied function. Defaults to ``"constant"``.
                See also: https://numpy.org/doc/1.18/reference/generated/numpy.pad.html
                https://pytorch.org/docs/stable/generated/torch.nn.functional.pad.html
                It also can be a sequence of string, each element corresponds to a key in ``keys``.
            allow_missing_keys: don't raise exception if key is missing.
            kwargs: other arguments for the `np.pad` or `torch.pad` function.
                note that `np.pad` treats channel dimension as the first dimension.

        """
        padder = SpatialPad(spatial_size, method, **kwargs)
        super().__init__(keys, padder=padder, mode=mode, allow_missing_keys=allow_missing_keys)


class BorderPadd(Padd):
    """
    Pad the input data by adding specified borders to every dimension.
    Dictionary-based wrapper of :py:class:`monai.transforms.BorderPad`.
    """

    backend = BorderPad.backend

    def __init__(
        self,
        keys: KeysCollection,
        spatial_border: Sequence[int] | int,
        mode: SequenceStr = PytorchPadMode.CONSTANT,
        allow_missing_keys: bool = False,
        **kwargs,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            spatial_border: specified size for every spatial border. it can be 3 shapes:

                - single int number, pad all the borders with the same size.
                - length equals the length of image shape, pad every spatial dimension separately.
                  for example, image shape(CHW) is [1, 4, 4], spatial_border is [2, 1],
                  pad every border of H dim with 2, pad every border of W dim with 1, result shape is [1, 8, 6].
                - length equals 2 x (length of image shape), pad every border of every dimension separately.
                  for example, image shape(CHW) is [1, 4, 4], spatial_border is [1, 2, 3, 4], pad top of H dim with 1,
                  pad bottom of H dim with 2, pad left of W dim with 3, pad right of W dim with 4.
                  the result shape is [1, 7, 11].

            mode: available modes for numpy array:{``"constant"``, ``"edge"``, ``"linear_ramp"``, ``"maximum"``,
                ``"mean"``, ``"median"``, ``"minimum"``, ``"reflect"``, ``"symmetric"``, ``"wrap"``, ``"empty"``}
                available modes for PyTorch Tensor: {``"constant"``, ``"reflect"``, ``"replicate"``, ``"circular"``}.
                One of the listed string values or a user supplied function. Defaults to ``"constant"``.
                See also: https://numpy.org/doc/1.18/reference/generated/numpy.pad.html
                https://pytorch.org/docs/stable/generated/torch.nn.functional.pad.html
                It also can be a sequence of string, each element corresponds to a key in ``keys``.
            allow_missing_keys: don't raise exception if key is missing.
            kwargs: other arguments for the `np.pad` or `torch.pad` function.
                note that `np.pad` treats channel dimension as the first dimension.

        """
        padder = BorderPad(spatial_border=spatial_border, **kwargs)
        super().__init__(keys, padder=padder, mode=mode, allow_missing_keys=allow_missing_keys)


class DivisiblePadd(Padd):
    """
    Pad the input data, so that the spatial sizes are divisible by `k`.
    Dictionary-based wrapper of :py:class:`monai.transforms.DivisiblePad`.
    """

    backend = DivisiblePad.backend

    def __init__(
        self,
        keys: KeysCollection,
        k: Sequence[int] | int,
        mode: SequenceStr = PytorchPadMode.CONSTANT,
        method: str = Method.SYMMETRIC,
        allow_missing_keys: bool = False,
        **kwargs,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            k: the target k for each spatial dimension.
                if `k` is negative or 0, the original size is preserved.
                if `k` is an int, the same `k` be applied to all the input spatial dimensions.
            mode: available modes for numpy array:{``"constant"``, ``"edge"``, ``"linear_ramp"``, ``"maximum"``,
                ``"mean"``, ``"median"``, ``"minimum"``, ``"reflect"``, ``"symmetric"``, ``"wrap"``, ``"empty"``}
                available modes for PyTorch Tensor: {``"constant"``, ``"reflect"``, ``"replicate"``, ``"circular"``}.
                One of the listed string values or a user supplied function. Defaults to ``"constant"``.
                See also: https://numpy.org/doc/1.18/reference/generated/numpy.pad.html
                https://pytorch.org/docs/stable/generated/torch.nn.functional.pad.html
                It also can be a sequence of string, each element corresponds to a key in ``keys``.
            method: {``"symmetric"``, ``"end"``}
                Pad image symmetrically on every side or only pad at the end sides. Defaults to ``"symmetric"``.
            allow_missing_keys: don't raise exception if key is missing.
            kwargs: other arguments for the `np.pad` or `torch.pad` function.
                note that `np.pad` treats channel dimension as the first dimension.

        See also :py:class:`monai.transforms.SpatialPad`

        """
        padder = DivisiblePad(k=k, method=method, **kwargs)
        super().__init__(keys, padder=padder, mode=mode, allow_missing_keys=allow_missing_keys)


class Cropd(MapTransform, InvertibleTransform):
    """
    Dictionary-based wrapper of abstract class :py:class:`monai.transforms.Crop`.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: :py:class:`monai.transforms.compose.MapTransform`
        cropper: crop transform for the input image.
        allow_missing_keys: don't raise exception if key is missing.

    """

    backend = Crop.backend

    def __init__(self, keys: KeysCollection, cropper: Crop, allow_missing_keys: bool = False):
        super().__init__(keys, allow_missing_keys)
        self.cropper = cropper

    def __call__(self, data: Mapping[Hashable, torch.Tensor]) -> dict[Hashable, torch.Tensor]:
        d = dict(data)
        for key in self.key_iterator(d):
            d[key] = self.cropper(d[key])  # type: ignore
        return d

    def inverse(self, data: Mapping[Hashable, MetaTensor]) -> dict[Hashable, MetaTensor]:
        d = dict(data)
        for key in self.key_iterator(d):
            d[key] = self.cropper.inverse(d[key])
        return d


class RandCropd(Cropd, Randomizable):
    """
    Base class for random crop transform.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: :py:class:`monai.transforms.compose.MapTransform`
        cropper: random crop transform for the input image.
        allow_missing_keys: don't raise exception if key is missing.

    """

    backend = Crop.backend

    def __init__(self, keys: KeysCollection, cropper: Crop, allow_missing_keys: bool = False):
        super().__init__(keys, cropper=cropper, allow_missing_keys=allow_missing_keys)

    def set_random_state(self, seed: int | None = None, state: np.random.RandomState | None = None) -> RandCropd:
        super().set_random_state(seed, state)
        if isinstance(self.cropper, Randomizable):
            self.cropper.set_random_state(seed, state)
        return self

    def randomize(self, img_size: Sequence[int]) -> None:
        if isinstance(self.cropper, Randomizable):
            self.cropper.randomize(img_size)

    def __call__(self, data: Mapping[Hashable, torch.Tensor]) -> dict[Hashable, torch.Tensor]:
        d = dict(data)
        # the first key must exist to execute random operations
        self.randomize(d[self.first_key(d)].shape[1:])
        for key in self.key_iterator(d):
            kwargs = {"randomize": False} if isinstance(self.cropper, Randomizable) else {}
            d[key] = self.cropper(d[key], **kwargs)  # type: ignore
        return d


class SpatialCropd(Cropd):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.SpatialCrop`.
    General purpose cropper to produce sub-volume region of interest (ROI).
    If a dimension of the expected ROI size is larger than the input image size, will not crop that dimension.
    So the cropped result may be smaller than the expected ROI, and the cropped results of several images may
    not have exactly the same shape.
    It can support to crop ND spatial (channel-first) data.

    The cropped region can be parameterised in various ways:
        - a list of slices for each spatial dimension (allows for use of -ve indexing and `None`)
        - a spatial center and size
        - the start and end coordinates of the ROI
    """

    def __init__(
        self,
        keys: KeysCollection,
        roi_center: Sequence[int] | None = None,
        roi_size: Sequence[int] | None = None,
        roi_start: Sequence[int] | None = None,
        roi_end: Sequence[int] | None = None,
        roi_slices: Sequence[slice] | None = None,
        allow_missing_keys: bool = False,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            roi_center: voxel coordinates for center of the crop ROI.
            roi_size: size of the crop ROI, if a dimension of ROI size is larger than image size,
                will not crop that dimension of the image.
            roi_start: voxel coordinates for start of the crop ROI.
            roi_end: voxel coordinates for end of the crop ROI, if a coordinate is out of image,
                use the end coordinate of image.
            roi_slices: list of slices for each of the spatial dimensions.
            allow_missing_keys: don't raise exception if key is missing.

        """
        cropper = SpatialCrop(roi_center, roi_size, roi_start, roi_end, roi_slices)
        super().__init__(keys, cropper=cropper, allow_missing_keys=allow_missing_keys)


class CenterSpatialCropd(Cropd):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.CenterSpatialCrop`.
    If a dimension of the expected ROI size is larger than the input image size, will not crop that dimension.
    So the cropped result may be smaller than the expected ROI, and the cropped results of several images may
    not have exactly the same shape.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: monai.transforms.MapTransform
        roi_size: the size of the crop region e.g. [224,224,128]
            if a dimension of ROI size is larger than image size, will not crop that dimension of the image.
            If its components have non-positive values, the corresponding size of input image will be used.
            for example: if the spatial size of input data is [40, 40, 40] and `roi_size=[32, 64, -1]`,
            the spatial size of output data will be [32, 40, 40].
        allow_missing_keys: don't raise exception if key is missing.
    """

    def __init__(self, keys: KeysCollection, roi_size: Sequence[int] | int, allow_missing_keys: bool = False) -> None:
        cropper = CenterSpatialCrop(roi_size)
        super().__init__(keys, cropper=cropper, allow_missing_keys=allow_missing_keys)


class CenterScaleCropd(Cropd):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.CenterScaleCrop`.
    Note: as using the same scaled ROI to crop, all the input data specified by `keys` should have
    the same spatial shape.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: monai.transforms.MapTransform
        roi_scale: specifies the expected scale of image size to crop. e.g. [0.3, 0.4, 0.5] or a number for all dims.
            If its components have non-positive values, will use `1.0` instead, which means the input image size.
        allow_missing_keys: don't raise exception if key is missing.
    """

    def __init__(
        self, keys: KeysCollection, roi_scale: Sequence[float] | float, allow_missing_keys: bool = False
    ) -> None:
        cropper = CenterScaleCrop(roi_scale)
        super().__init__(keys, cropper=cropper, allow_missing_keys=allow_missing_keys)


class RandSpatialCropd(RandCropd):
    """
    Dictionary-based version :py:class:`monai.transforms.RandSpatialCrop`.
    Crop image with random size or specific size ROI. It can crop at a random position as
    center or at the image center. And allows to set the minimum and maximum size to limit the randomly
    generated ROI. Suppose all the expected fields specified by `keys` have same shape.

    Note: even `random_size=False`, if a dimension of the expected ROI size is larger than the input image size,
    will not crop that dimension. So the cropped result may be smaller than the expected ROI, and the cropped
    results of several images may not have exactly the same shape.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: monai.transforms.MapTransform
        roi_size: if `random_size` is True, it specifies the minimum crop region.
            if `random_size` is False, it specifies the expected ROI size to crop. e.g. [224, 224, 128]
            if a dimension of ROI size is larger than image size, will not crop that dimension of the image.
            If its components have non-positive values, the corresponding size of input image will be used.
            for example: if the spatial size of input data is [40, 40, 40] and `roi_size=[32, 64, -1]`,
            the spatial size of output data will be [32, 40, 40].
        max_roi_size: if `random_size` is True and `roi_size` specifies the min crop region size, `max_roi_size`
            can specify the max crop region size. if None, defaults to the input image size.
            if its components have non-positive values, the corresponding size of input image will be used.
        random_center: crop at random position as center or the image center.
        random_size: crop with random size or specific size ROI.
            if True, the actual size is sampled from:
            `randint(roi_scale * image spatial size, max_roi_scale * image spatial size + 1)`.
        allow_missing_keys: don't raise exception if key is missing.
    """

    def __init__(
        self,
        keys: KeysCollection,
        roi_size: Sequence[int] | int,
        max_roi_size: Sequence[int] | int | None = None,
        random_center: bool = True,
        random_size: bool = True,
        allow_missing_keys: bool = False,
    ) -> None:
        cropper = RandSpatialCrop(roi_size, max_roi_size, random_center, random_size)
        super().__init__(keys, cropper=cropper, allow_missing_keys=allow_missing_keys)


class RandScaleCropd(RandCropd):
    """
    Dictionary-based version :py:class:`monai.transforms.RandScaleCrop`.
    Crop image with random size or specific size ROI.
    It can crop at a random position as center or at the image center.
    And allows to set the minimum and maximum scale of image size to limit the randomly generated ROI.
    Suppose all the expected fields specified by `keys` have same shape.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: monai.transforms.MapTransform
        roi_scale: if `random_size` is True, it specifies the minimum crop size: `roi_scale * image spatial size`.
            if `random_size` is False, it specifies the expected scale of image size to crop. e.g. [0.3, 0.4, 0.5].
            If its components have non-positive values, will use `1.0` instead, which means the input image size.
        max_roi_scale: if `random_size` is True and `roi_scale` specifies the min crop region size, `max_roi_scale`
            can specify the max crop region size: `max_roi_scale * image spatial size`.
            if None, defaults to the input image size. if its components have non-positive values,
            will use `1.0` instead, which means the input image size.
        random_center: crop at random position as center or the image center.
        random_size: crop with random size or specified size ROI by `roi_scale * image spatial size`.
            if True, the actual size is sampled from:
            `randint(roi_scale * image spatial size, max_roi_scale * image spatial size + 1)`.
        allow_missing_keys: don't raise exception if key is missing.
    """

    def __init__(
        self,
        keys: KeysCollection,
        roi_scale: Sequence[float] | float,
        max_roi_scale: Sequence[float] | float | None = None,
        random_center: bool = True,
        random_size: bool = True,
        allow_missing_keys: bool = False,
    ) -> None:
        cropper = RandScaleCrop(roi_scale, max_roi_scale, random_center, random_size)
        super().__init__(keys, cropper=cropper, allow_missing_keys=allow_missing_keys)


class RandSpatialCropSamplesd(Randomizable, MapTransform):
    """
    Dictionary-based version :py:class:`monai.transforms.RandSpatialCropSamples`.
    Crop image with random size or specific size ROI to generate a list of N samples.
    It can crop at a random position as center or at the image center. And allows to set
    the minimum size to limit the randomly generated ROI. Suppose all the expected fields
    specified by `keys` have same shape, and add `patch_index` to the corresponding metadata.
    It will return a list of dictionaries for all the cropped images.

    Note: even `random_size=False`, if a dimension of the expected ROI size is larger than the input image size,
    will not crop that dimension. So the cropped result may be smaller than the expected ROI, and the cropped
    results of several images may not have exactly the same shape.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: monai.transforms.MapTransform
        roi_size: if `random_size` is True, it specifies the minimum crop region.
            if `random_size` is False, it specifies the expected ROI size to crop. e.g. [224, 224, 128]
            if a dimension of ROI size is larger than image size, will not crop that dimension of the image.
            If its components have non-positive values, the corresponding size of input image will be used.
            for example: if the spatial size of input data is [40, 40, 40] and `roi_size=[32, 64, -1]`,
            the spatial size of output data will be [32, 40, 40].
        num_samples: number of samples (crop regions) to take in the returned list.
        max_roi_size: if `random_size` is True and `roi_size` specifies the min crop region size, `max_roi_size`
            can specify the max crop region size. if None, defaults to the input image size.
            if its components have non-positive values, the corresponding size of input image will be used.
        random_center: crop at random position as center or the image center.
        random_size: crop with random size or specific size ROI.
            The actual size is sampled from `randint(roi_size, img_size)`.
        allow_missing_keys: don't raise exception if key is missing.

    Raises:
        ValueError: When ``num_samples`` is nonpositive.

    """

    backend = RandSpatialCropSamples.backend

    @deprecated_arg(name="meta_keys", since="0.9")
    @deprecated_arg(name="meta_key_postfix", since="0.9")
    def __init__(
        self,
        keys: KeysCollection,
        roi_size: Sequence[int] | int,
        num_samples: int,
        max_roi_size: Sequence[int] | int | None = None,
        random_center: bool = True,
        random_size: bool = True,
        meta_keys: KeysCollection | None = None,
        meta_key_postfix: str = "meta_dict",
        allow_missing_keys: bool = False,
    ) -> None:
        MapTransform.__init__(self, keys, allow_missing_keys)
        self.cropper = RandSpatialCropSamples(roi_size, num_samples, max_roi_size, random_center, random_size)

    def randomize(self, data: Any | None = None) -> None:
        self.sub_seed = self.R.randint(MAX_SEED, dtype="uint32")

    def __call__(self, data: Mapping[Hashable, torch.Tensor]) -> list[dict[Hashable, torch.Tensor]]:
        ret: list[dict[Hashable, torch.Tensor]] = [dict(data) for _ in range(self.cropper.num_samples)]
        # deep copy all the unmodified data
        for i in range(self.cropper.num_samples):
            for key in set(data.keys()).difference(set(self.keys)):
                ret[i][key] = deepcopy(data[key])

        # for each key we reset the random state to ensure crops are the same
        self.randomize()
        for key in self.key_iterator(dict(data)):
            self.cropper.set_random_state(seed=self.sub_seed)
            for i, im in enumerate(self.cropper(data[key])):
                ret[i][key] = im
        return ret


class CropForegroundd(Cropd):
    """
    Dictionary-based version :py:class:`monai.transforms.CropForeground`.
    Crop only the foreground object of the expected images.
    The typical usage is to help training and evaluation if the valid part is small in the whole medical image.
    The valid part can be determined by any field in the data with `source_key`, for example:
    - Select values > 0 in image field as the foreground and crop on all fields specified by `keys`.
    - Select label = 3 in label field as the foreground to crop on all fields specified by `keys`.
    - Select label > 0 in the third channel of a One-Hot label field as the foreground to crop all `keys` fields.
    Users can define arbitrary function to select expected foreground from the whole source image or specified
    channels. And it can also add margin to every dim of the bounding box of foreground object.
    """

    def __init__(
        self,
        keys: KeysCollection,
        source_key: str,
        select_fn: Callable = is_positive,
        channel_indices: IndexSelection | None = None,
        margin: Sequence[int] | int = 0,
        allow_smaller: bool = True,
        k_divisible: Sequence[int] | int = 1,
        mode: SequenceStr = PytorchPadMode.CONSTANT,
        start_coord_key: str = "foreground_start_coord",
        end_coord_key: str = "foreground_end_coord",
        allow_missing_keys: bool = False,
        **pad_kwargs,
    ) -> None:
        """
        Args:
            keys: keys of the corresponding items to be transformed.
                See also: :py:class:`monai.transforms.compose.MapTransform`
            source_key: data source to generate the bounding box of foreground, can be image or label, etc.
            select_fn: function to select expected foreground, default is to select values > 0.
            channel_indices: if defined, select foreground only on the specified channels
                of image. if None, select foreground on the whole image.
            margin: add margin value to spatial dims of the bounding box, if only 1 value provided, use it for all dims.
            allow_smaller: when computing box size with `margin`, whether allow the image size to be smaller
                than box size, default to `True`. if the margined size is larger than image size, will pad with
                specified `mode`.
            k_divisible: make each spatial dimension to be divisible by k, default to 1.
                if `k_divisible` is an int, the same `k` be applied to all the input spatial dimensions.
            mode: available modes for numpy array:{``"constant"``, ``"edge"``, ``"linear_ramp"``, ``"maximum"``,
                ``"mean"``, ``"median"``, ``"minimum"``, ``"reflect"``, ``"symmetric"``, ``"wrap"``, ``"empty"``}
                available modes for PyTorch Tensor: {``"constant"``, ``"reflect"``, ``"replicate"``, ``"circular"``}.
                One of the listed string values or a user supplied function. Defaults to ``"constant"``.
                See also: https://numpy.org/doc/1.18/reference/generated/numpy.pad.html
                https://pytorch.org/docs/stable/generated/torch.nn.functional.pad.html
                it also can be a sequence of string, each element corresponds to a key in ``keys``.
            start_coord_key: key to record the start coordinate of spatial bounding box for foreground.
            end_coord_key: key to record the end coordinate of spatial bounding box for foreground.
            allow_missing_keys: don't raise exception if key is missing.
            pad_kwargs: other arguments for the `np.pad` or `torch.pad` function.
                note that `np.pad` treats channel dimension as the first dimension.

        """
        self.source_key = source_key
        self.start_coord_key = start_coord_key
        self.end_coord_key = end_coord_key
        cropper = CropForeground(
            select_fn=select_fn,
            channel_indices=channel_indices,
            margin=margin,
            allow_smaller=allow_smaller,
            k_divisible=k_divisible,
            **pad_kwargs,
        )
        super().__init__(keys, cropper=cropper, allow_missing_keys=allow_missing_keys)
        self.mode = ensure_tuple_rep(mode, len(self.keys))

    def __call__(self, data: Mapping[Hashable, torch.Tensor]) -> dict[Hashable, torch.Tensor]:
        d = dict(data)
        self.cropper: CropForeground
        box_start, box_end = self.cropper.compute_bounding_box(img=d[self.source_key])
        if self.start_coord_key is not None:
            d[self.start_coord_key] = box_start
        if self.end_coord_key is not None:
            d[self.end_coord_key] = box_end
        for key, m in self.key_iterator(d, self.mode):
            d[key] = self.cropper.crop_pad(img=d[key], box_start=box_start, box_end=box_end, mode=m)
        return d


class RandWeightedCropd(Randomizable, MapTransform):
    """
    Samples a list of `num_samples` image patches according to the provided `weight_map`.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: :py:class:`monai.transforms.compose.MapTransform`
        w_key: key for the weight map. The corresponding value will be used as the sampling weights,
            it should be a single-channel array in size, for example, `(1, spatial_dim_0, spatial_dim_1, ...)`
        spatial_size: the spatial size of the image patch e.g. [224, 224, 128].
            If its components have non-positive values, the corresponding size of `img` will be used.
        num_samples: number of samples (image patches) to take in the returned list.
        allow_missing_keys: don't raise exception if key is missing.

    See Also:
        :py:class:`monai.transforms.RandWeightedCrop`
    """

    backend = SpatialCrop.backend

    @deprecated_arg(name="meta_keys", since="0.9")
    @deprecated_arg(name="meta_key_postfix", since="0.9")
    @deprecated_arg(name="center_coord_key", since="0.9", msg_suffix="coords stored in img.meta['crop_center']")
    def __init__(
        self,
        keys: KeysCollection,
        w_key: str,
        spatial_size: Sequence[int] | int,
        num_samples: int = 1,
        center_coord_key: str | None = None,
        meta_keys: KeysCollection | None = None,
        meta_key_postfix: str = "meta_dict",
        allow_missing_keys: bool = False,
    ):
        MapTransform.__init__(self, keys, allow_missing_keys)
        self.w_key = w_key
        self.cropper = RandWeightedCrop(spatial_size, num_samples)

    def set_random_state(
        self, seed: int | None = None, state: np.random.RandomState | None = None
    ) -> RandWeightedCropd:
        super().set_random_state(seed, state)
        self.cropper.set_random_state(seed, state)
        return self

    def randomize(self, weight_map: NdarrayOrTensor) -> None:
        self.cropper.randomize(weight_map)

    def __call__(self, data: Mapping[Hashable, torch.Tensor]) -> list[dict[Hashable, torch.Tensor]]:
        # output starts as empty list of dictionaries
        ret: list = [dict(data) for _ in range(self.cropper.num_samples)]
        # deep copy all the unmodified data
        for i in range(self.cropper.num_samples):
            for key in set(data.keys()).difference(set(self.keys)):
                ret[i][key] = deepcopy(data[key])

        self.randomize(weight_map=data[self.w_key])
        for key in self.key_iterator(data):
            for i, im in enumerate(self.cropper(data[key], weight_map=data[self.w_key], randomize=False)):
                ret[i][key] = im
        return ret


class RandCropByPosNegLabeld(Randomizable, MapTransform):
    """
    Dictionary-based version :py:class:`monai.transforms.RandCropByPosNegLabel`.
    Crop random fixed sized regions with the center being a foreground or background voxel
    based on the Pos Neg Ratio.
    Suppose all the expected fields specified by `keys` have same shape,
    and add `patch_index` to the corresponding metadata.
    And will return a list of dictionaries for all the cropped images.

    If a dimension of the expected spatial size is larger than the input image size,
    will not crop that dimension. So the cropped result may be smaller than the expected size,
    and the cropped results of several images may not have exactly the same shape.
    And if the crop ROI is partly out of the image, will automatically adjust the crop center
    to ensure the valid crop ROI.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: :py:class:`monai.transforms.compose.MapTransform`
        label_key: name of key for label image, this will be used for finding foreground/background.
        spatial_size: the spatial size of the crop region e.g. [224, 224, 128].
            if a dimension of ROI size is larger than image size, will not crop that dimension of the image.
            if its components have non-positive values, the corresponding size of `data[label_key]` will be used.
            for example: if the spatial size of input data is [40, 40, 40] and `spatial_size=[32, 64, -1]`,
            the spatial size of output data will be [32, 40, 40].
        pos: used with `neg` together to calculate the ratio ``pos / (pos + neg)`` for the probability
            to pick a foreground voxel as a center rather than a background voxel.
        neg: used with `pos` together to calculate the ratio ``pos / (pos + neg)`` for the probability
            to pick a foreground voxel as a center rather than a background voxel.
        num_samples: number of samples (crop regions) to take in each list.
        image_key: if image_key is not None, use ``label == 0 & image > image_threshold`` to select
            the negative sample(background) center. so the crop center will only exist on valid image area.
        image_threshold: if enabled image_key, use ``image > image_threshold`` to determine
            the valid image content area.
        fg_indices_key: if provided pre-computed foreground indices of `label`, will ignore above `image_key` and
            `image_threshold`, and randomly select crop centers based on them, need to provide `fg_indices_key`
            and `bg_indices_key` together, expect to be 1 dim array of spatial indices after flattening.
            a typical usage is to call `FgBgToIndicesd` transform first and cache the results.
        bg_indices_key: if provided pre-computed background indices of `label`, will ignore above `image_key` and
            `image_threshold`, and randomly select crop centers based on them, need to provide `fg_indices_key`
            and `bg_indices_key` together, expect to be 1 dim array of spatial indices after flattening.
            a typical usage is to call `FgBgToIndicesd` transform first and cache the results.
        allow_smaller: if `False`, an exception will be raised if the image is smaller than
            the requested ROI in any dimension. If `True`, any smaller dimensions will be set to
            match the cropped size (i.e., no cropping in that dimension).
        allow_missing_keys: don't raise exception if key is missing.

    Raises:
        ValueError: When ``pos`` or ``neg`` are negative.
        ValueError: When ``pos=0`` and ``neg=0``. Incompatible values.

    """

    backend = RandCropByPosNegLabel.backend

    @deprecated_arg(name="meta_keys", since="0.9")
    @deprecated_arg(name="meta_key_postfix", since="0.9")
    def __init__(
        self,
        keys: KeysCollection,
        label_key: str,
        spatial_size: Sequence[int] | int,
        pos: float = 1.0,
        neg: float = 1.0,
        num_samples: int = 1,
        image_key: str | None = None,
        image_threshold: float = 0.0,
        fg_indices_key: str | None = None,
        bg_indices_key: str | None = None,
        meta_keys: KeysCollection | None = None,
        meta_key_postfix: str = "meta_dict",
        allow_smaller: bool = False,
        allow_missing_keys: bool = False,
    ) -> None:
        MapTransform.__init__(self, keys, allow_missing_keys)
        self.label_key = label_key
        self.image_key = image_key
        self.fg_indices_key = fg_indices_key
        self.bg_indices_key = bg_indices_key
        self.cropper = RandCropByPosNegLabel(
            spatial_size=spatial_size,
            pos=pos,
            neg=neg,
            num_samples=num_samples,
            image_threshold=image_threshold,
            allow_smaller=allow_smaller,
        )

    def set_random_state(
        self, seed: int | None = None, state: np.random.RandomState | None = None
    ) -> RandCropByPosNegLabeld:
        super().set_random_state(seed, state)
        self.cropper.set_random_state(seed, state)
        return self

    def randomize(
        self,
        label: torch.Tensor,
        fg_indices: NdarrayOrTensor | None = None,
        bg_indices: NdarrayOrTensor | None = None,
        image: torch.Tensor | None = None,
    ) -> None:
        self.cropper.randomize(label=label, fg_indices=fg_indices, bg_indices=bg_indices, image=image)

    def __call__(self, data: Mapping[Hashable, torch.Tensor]) -> list[dict[Hashable, torch.Tensor]]:
        d = dict(data)
        label = d[self.label_key]
        image = d[self.image_key] if self.image_key else None
        fg_indices = d.pop(self.fg_indices_key, None) if self.fg_indices_key is not None else None
        bg_indices = d.pop(self.bg_indices_key, None) if self.bg_indices_key is not None else None

        self.randomize(label, fg_indices, bg_indices, image)

        # initialize returned list with shallow copy to preserve key ordering
        ret: list = [dict(d) for _ in range(self.cropper.num_samples)]
        # deep copy all the unmodified data
        for i in range(self.cropper.num_samples):
            for key in set(d.keys()).difference(set(self.keys)):
                ret[i][key] = deepcopy(d[key])

        for key in self.key_iterator(d):
            for i, im in enumerate(self.cropper(d[key], label=label, randomize=False)):
                ret[i][key] = im
        return ret


class RandCropByLabelClassesd(Randomizable, MapTransform):
    """
    Dictionary-based version :py:class:`monai.transforms.RandCropByLabelClasses`.
    Crop random fixed sized regions with the center being a class based on the specified ratios of every class.
    The label data can be One-Hot format array or Argmax data. And will return a list of arrays for all the
    cropped images. For example, crop two (3 x 3) arrays from (5 x 5) array with `ratios=[1, 2, 3, 1]`::

        cropper = RandCropByLabelClassesd(
            keys=["image", "label"],
            label_key="label",
            spatial_size=[3, 3],
            ratios=[1, 2, 3, 1],
            num_classes=4,
            num_samples=2,
        )
        data = {
            "image": np.array([
                [[0.0, 0.3, 0.4, 0.2, 0.0],
                [0.0, 0.1, 0.2, 0.1, 0.4],
                [0.0, 0.3, 0.5, 0.2, 0.0],
                [0.1, 0.2, 0.1, 0.1, 0.0],
                [0.0, 0.1, 0.2, 0.1, 0.0]]
            ]),
            "label": np.array([
                [[0, 0, 0, 0, 0],
                [0, 1, 2, 1, 0],
                [0, 1, 3, 0, 0],
                [0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0]]
            ]),
        }
        result = cropper(data)

        The 2 randomly cropped samples of `label` can be:
        [[0, 1, 2],     [[0, 0, 0],
         [0, 1, 3],      [1, 2, 1],
         [0, 0, 0]]      [1, 3, 0]]

    If a dimension of the expected spatial size is larger than the input image size,
    will not crop that dimension. So the cropped result may be smaller than expected size, and the cropped
    results of several images may not have exactly same shape.
    And if the crop ROI is partly out of the image, will automatically adjust the crop center to ensure the
    valid crop ROI.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: :py:class:`monai.transforms.compose.MapTransform`
        label_key: name of key for label image, this will be used for finding indices of every class.
        spatial_size: the spatial size of the crop region e.g. [224, 224, 128].
            if a dimension of ROI size is larger than image size, will not crop that dimension of the image.
            if its components have non-positive values, the corresponding size of `label` will be used.
            for example: if the spatial size of input data is [40, 40, 40] and `spatial_size=[32, 64, -1]`,
            the spatial size of output data will be [32, 40, 40].
        ratios: specified ratios of every class in the label to generate crop centers, including background class.
            if None, every class will have the same ratio to generate crop centers.
        num_classes: number of classes for argmax label, not necessary for One-Hot label.
        num_samples: number of samples (crop regions) to take in each list.
        image_key: if image_key is not None, only return the indices of every class that are within the valid
            region of the image (``image > image_threshold``).
        image_threshold: if enabled `image_key`, use ``image > image_threshold`` to
            determine the valid image content area and select class indices only in this area.
        indices_key: if provided pre-computed indices of every class, will ignore above `image` and
            `image_threshold`, and randomly select crop centers based on them, expect to be 1 dim array
            of spatial indices after flattening. a typical usage is to call `ClassesToIndices` transform first
            and cache the results for better performance.
        allow_smaller: if `False`, an exception will be raised if the image is smaller than
            the requested ROI in any dimension. If `True`, any smaller dimensions will remain
            unchanged.
        allow_missing_keys: don't raise exception if key is missing.

    """

    backend = RandCropByLabelClasses.backend

    @deprecated_arg(name="meta_keys", since="0.9")
    @deprecated_arg(name="meta_key_postfix", since="0.9")
    def __init__(
        self,
        keys: KeysCollection,
        label_key: str,
        spatial_size: Sequence[int] | int,
        ratios: list[float | int] | None = None,
        num_classes: int | None = None,
        num_samples: int = 1,
        image_key: str | None = None,
        image_threshold: float = 0.0,
        indices_key: str | None = None,
        meta_keys: KeysCollection | None = None,
        meta_key_postfix: str = "meta_dict",
        allow_smaller: bool = False,
        allow_missing_keys: bool = False,
    ) -> None:
        MapTransform.__init__(self, keys, allow_missing_keys)
        self.label_key = label_key
        self.image_key = image_key
        self.indices_key = indices_key
        self.cropper = RandCropByLabelClasses(
            spatial_size=spatial_size,
            ratios=ratios,
            num_classes=num_classes,
            num_samples=num_samples,
            image_threshold=image_threshold,
            allow_smaller=allow_smaller,
        )

    def set_random_state(
        self, seed: int | None = None, state: np.random.RandomState | None = None
    ) -> RandCropByLabelClassesd:
        super().set_random_state(seed, state)
        self.cropper.set_random_state(seed, state)
        return self

    def randomize(
        self, label: torch.Tensor, indices: list[NdarrayOrTensor] | None = None, image: torch.Tensor | None = None
    ) -> None:
        self.cropper.randomize(label=label, indices=indices, image=image)

    def __call__(self, data: Mapping[Hashable, Any]) -> list[dict[Hashable, torch.Tensor]]:
        d = dict(data)
        label = d[self.label_key]
        image = d[self.image_key] if self.image_key else None
        indices = d.pop(self.indices_key, None) if self.indices_key is not None else None

        self.randomize(label, indices, image)

        # initialize returned list with shallow copy to preserve key ordering
        ret: list = [dict(d) for _ in range(self.cropper.num_samples)]
        # deep copy all the unmodified data
        for i in range(self.cropper.num_samples):
            for key in set(d.keys()).difference(set(self.keys)):
                ret[i][key] = deepcopy(d[key])

        for key in self.key_iterator(d):
            for i, im in enumerate(self.cropper(d[key], label=label, randomize=False)):
                ret[i][key] = im
        return ret


class ResizeWithPadOrCropd(Padd):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.ResizeWithPadOrCrop`.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: monai.transforms.MapTransform
        spatial_size: the spatial size of output data after padding or crop.
            If has non-positive values, the corresponding size of input image will be used (no padding).
        mode: available modes for numpy array:{``"constant"``, ``"edge"``, ``"linear_ramp"``, ``"maximum"``,
            ``"mean"``, ``"median"``, ``"minimum"``, ``"reflect"``, ``"symmetric"``, ``"wrap"``, ``"empty"``}
            available modes for PyTorch Tensor: {``"constant"``, ``"reflect"``, ``"replicate"``, ``"circular"``}.
            One of the listed string values or a user supplied function. Defaults to ``"constant"``.
            See also: https://numpy.org/doc/1.18/reference/generated/numpy.pad.html
            https://pytorch.org/docs/stable/generated/torch.nn.functional.pad.html
            It also can be a sequence of string, each element corresponds to a key in ``keys``.
        allow_missing_keys: don't raise exception if key is missing.
        method: {``"symmetric"``, ``"end"``}
            Pad image symmetrically on every side or only pad at the end sides. Defaults to ``"symmetric"``.
        pad_kwargs: other arguments for the `np.pad` or `torch.pad` function.
            note that `np.pad` treats channel dimension as the first dimension.

    """

    def __init__(
        self,
        keys: KeysCollection,
        spatial_size: Sequence[int] | int,
        mode: SequenceStr = PytorchPadMode.CONSTANT,
        allow_missing_keys: bool = False,
        method: str = Method.SYMMETRIC,
        **pad_kwargs,
    ) -> None:
        padcropper = ResizeWithPadOrCrop(spatial_size=spatial_size, method=method, **pad_kwargs)
        super().__init__(keys, padder=padcropper, mode=mode, allow_missing_keys=allow_missing_keys)  # type: ignore


class BoundingRectd(MapTransform):
    """
    Dictionary-based wrapper of :py:class:`monai.transforms.BoundingRect`.

    Args:
        keys: keys of the corresponding items to be transformed.
            See also: monai.transforms.MapTransform
        bbox_key_postfix: the output bounding box coordinates will be
            written to the value of `{key}_{bbox_key_postfix}`.
        select_fn: function to select expected foreground, default is to select values > 0.
        allow_missing_keys: don't raise exception if key is missing.
    """

    backend = BoundingRect.backend

    def __init__(
        self,
        keys: KeysCollection,
        bbox_key_postfix: str = "bbox",
        select_fn: Callable = is_positive,
        allow_missing_keys: bool = False,
    ):
        super().__init__(keys, allow_missing_keys)
        self.bbox = BoundingRect(select_fn=select_fn)
        self.bbox_key_postfix = bbox_key_postfix

    def __call__(self, data: Mapping[Hashable, NdarrayOrTensor]) -> dict[Hashable, NdarrayOrTensor]:
        """
        See also: :py:class:`monai.transforms.utils.generate_spatial_bounding_box`.
        """
        d = dict(data)
        for key in self.key_iterator(d):
            bbox = self.bbox(d[key])
            key_to_add = f"{key}_{self.bbox_key_postfix}"
            if key_to_add in d:
                raise KeyError(f"Bounding box data with key {key_to_add} already exists.")
            d[key_to_add] = bbox
        return d


PadD = PadDict = Padd
SpatialPadD = SpatialPadDict = SpatialPadd
BorderPadD = BorderPadDict = BorderPadd
DivisiblePadD = DivisiblePadDict = DivisiblePadd
CropD = CropDict = Cropd
RandCropD = RandCropDict = RandCropd
SpatialCropD = SpatialCropDict = SpatialCropd
CenterSpatialCropD = CenterSpatialCropDict = CenterSpatialCropd
CenterScaleCropD = CenterScaleCropDict = CenterScaleCropd
RandSpatialCropD = RandSpatialCropDict = RandSpatialCropd
RandScaleCropD = RandScaleCropDict = RandScaleCropd
RandSpatialCropSamplesD = RandSpatialCropSamplesDict = RandSpatialCropSamplesd
CropForegroundD = CropForegroundDict = CropForegroundd
RandWeightedCropD = RandWeightedCropDict = RandWeightedCropd
RandCropByPosNegLabelD = RandCropByPosNegLabelDict = RandCropByPosNegLabeld
RandCropByLabelClassesD = RandCropByLabelClassesDict = RandCropByLabelClassesd
ResizeWithPadOrCropD = ResizeWithPadOrCropDict = ResizeWithPadOrCropd
BoundingRectD = BoundingRectDict = BoundingRectd
