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
from pathlib import Path
import yaml
from bigdl.nano.utils.inference.pytorch.model import AcceleratedLightningModule
from ..core import version as inc_version
from neural_compressor.utils.pytorch import load
from neural_compressor.model.model import PyTorchModel
from bigdl.nano.utils.log4Error import invalidInputError
from bigdl.nano.pytorch.context_manager import generate_context_manager


class PytorchQuantizedModel(AcceleratedLightningModule):
    def __init__(self, model, thread_num=None):
        super().__init__(model.model)
        self.quantized = model
        self.thread_num = thread_num
        self.context_manager = generate_context_manager(accelerator=None,
                                                        precision="int8",
                                                        thread_num=thread_num)

    @property
    def _nargs(self):
        return -1

    @property
    def status(self):
        status = super().status
        status.update({"thread_num": self.thread_num})
        return status

    @staticmethod
    def _load(path, model):
        status = PytorchQuantizedModel._load_status(path)
        invalidInputError(
            model is not None,
            errMsg="FP32 model is required to create a quantized model."
        )
        qmodel = PyTorchModel(load(path, model))
        from packaging import version
        if version.parse(inc_version) < version.parse("1.11"):
            path = Path(path)
            tune_cfg_file = path / 'best_configure.yaml'
            with open(tune_cfg_file, 'r') as f:
                tune_cfg = yaml.safe_load(f)
                qmodel.tune_cfg = tune_cfg
        thread_num = None
        if status["thread_num"] is not None and status['thread_num'] != {}:
            thread_num = int(status["thread_num"])
        return PytorchQuantizedModel(qmodel, thread_num=thread_num)

    def _save_model(self, path):
        self.quantized.save(path)
