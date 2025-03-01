#
# Copyright 2016 The BigDL Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from bigdl.nano.utils.inference.pytorch.model_utils import get_forward_args
from typing import Sequence
from copy import deepcopy
import torch
import warnings


def transform_multiple_input_dataloader_to_inc_mode(model, dataloader):
    need_transformation, forward_args_len = _need_dataloader_type_transformation(model, dataloader)
    if need_transformation:
        # define a decorator to change multiple inputs to 2 items
        def tuple_collate_fn_wrapper(func, forward_args_len):
            def collate_fn(batch):
                res = func(batch)
                if len(res) - forward_args_len == 1:
                    # if only one y is provided
                    return tuple(res[:forward_args_len]), res[-1]
                else:
                    # if multiple y are provided
                    return tuple(res[:forward_args_len]), tuple(res[forward_args_len:])
            return collate_fn

        # deepcopy the dataloader so that the transformation will not pollute the original one
        new_dataloader = deepcopy(dataloader)

        # add collate fn to the dataloader
        new_dataloader.collate_fn = tuple_collate_fn_wrapper(new_dataloader.collate_fn,
                                                             forward_args_len)

        return new_dataloader
    return dataloader


def automatic_add_label_in_dataloader(model, dataloader, input_sample=None):
    if _check_whether_add_label(model, dataloader, input_sample) is True:
        # need to add label automaticly
        # generate a warning for user first
        warnings.warn("After checking, it is found that your data does not contain a label item. "
                      "In order to make quantification work normally, we will automatically "
                      "generate a dummy label.")

        # define a decorator to add label
        def label_collate_fn_wrapper(func):
            def collate_fn(batch):
                res = func(batch)
                # add dummy label
                return res, torch.ones(1).long()
            return collate_fn

        # construct a new dataloader
        new_dataloader = deepcopy(dataloader)
        new_dataloader.collate_fn = label_collate_fn_wrapper(new_dataloader.collate_fn)
        return new_dataloader
    return dataloader


def _need_dataloader_type_transformation(model, dataloader):
    # get forward method's parameter number
    forward_args = get_forward_args(model)
    forward_args_len = len(forward_args)

    # if the model is a simple model(x) format
    # we don't need to transform the dataloader
    # a special case is 0, this means *args is used in
    # users' forward method, we will also skip it as well
    if forward_args_len <= 1:
        return False, forward_args_len

    # check if a dataloader has met inc format
    input_sample = next(iter(dataloader))
    if isinstance(input_sample[0], Sequence):
        if len(input_sample[0]) == forward_args_len:
            return False, forward_args_len
    return True, forward_args_len


def _check_whether_add_label(model, dataloader, input_sample=None):
    # get forward method's parameter number and input sample
    forward_args = get_forward_args(model)
    forward_args_len = len(forward_args)
    loader_input_sample = next(iter(dataloader))

    if isinstance(loader_input_sample, torch.Tensor):
        if forward_args_len >= 1:
            return True
    elif isinstance(loader_input_sample, Sequence):
        if len(loader_input_sample[0]) == forward_args_len:
            return False
        else:
            if len(loader_input_sample) > forward_args_len:
                return False
            else:
                # test run to check if input_sample meet input requirent
                try:
                    model(*input_sample)
                    # additional check for kwargs paramter
                    if input_sample is not None and len(loader_input_sample) > len(input_sample):
                        return False
                    return True
                except RuntimeError:
                    # input sample may contain label already
                    pass
    return False
