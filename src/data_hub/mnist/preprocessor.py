import torch
from typing import Tuple
import codecs
import numpy as np
from data_hub.dataset.preprocesor import PreprocessingHelpers
from data_hub.io.resources import ResourceFactory, StreamedResource
import io
from data_hub.io.storage_connectors import StorageConnector


class MNISTPreprocessor:

    def __init__(self, storage_connector: StorageConnector):
        self.storage_connector = storage_connector

    def preprocess(self, raw_sample_identifier: str, raw_target_identifier: str, sample_identifier: str, target_identifier:str) -> Tuple[StreamedResource]:
        sample_resource = self._preprocess_sample_resource(raw_sample_identifier, sample_identifier)
        target_resource = self._preprocess_target_resource(raw_target_identifier, target_identifier)
        return sample_resource, target_resource

    def _torch_tensor_to_streamed_resource(self, identifier: str, tensor: torch.Tensor) -> StreamedResource:
        buffer = io.BytesIO()
        torch.save(tensor, buffer)
        resource = ResourceFactory.get_resource(identifier=identifier, file_like_object=buffer, in_memory=False)
        return resource

    def _preprocess_target_resource(self, raw_identifier: str, prep_identifier: str) -> StreamedResource:
        with self.storage_connector.get_resource(raw_identifier) as raw_resource:
            with PreprocessingHelpers.get_gzip_stream(resource=raw_resource) as unzipped_resource:
                torch_tensor = MNISTPreprocessor._read_label_file(unzipped_resource)
        resource = self._torch_tensor_to_streamed_resource(prep_identifier, torch_tensor)
        return resource

    def _preprocess_sample_resource(self, raw_identifier: str, prep_identifier: str) -> StreamedResource:
        with self.storage_connector.get_resource(raw_identifier) as raw_resource:
            with PreprocessingHelpers.get_gzip_stream(resource=raw_resource) as unzipped_resource:
                torch_tensor = MNISTPreprocessor._read_image_file(unzipped_resource)
        resource = self._torch_tensor_to_streamed_resource(prep_identifier, torch_tensor)
        return resource

    @classmethod
    def _get_int(cls, b):
        return int(codecs.encode(b, 'hex'), 16)

    @classmethod
    def _read_label_file(cls, resource: StreamedResource):
        data = resource.read()
        assert cls._get_int(data[:4]) == 2049
        length = cls._get_int(data[4:8])
        parsed = np.frombuffer(data, dtype=np.uint8, offset=8)
        torch_tensor = torch.from_numpy(parsed).view(length).long()
        torch_tensor = torch_tensor.long()
        return torch_tensor

    @classmethod
    def _read_image_file(cls, resource: StreamedResource):
        data = resource.read()
        assert cls._get_int(data[:4]) == 2051
        length = cls._get_int(data[4:8])
        num_rows = cls._get_int(data[8:12])
        num_cols = cls._get_int(data[12:16])
        parsed = np.frombuffer(data, dtype=np.uint8, offset=16)
        torch_tensor = torch.from_numpy(parsed).view(length, num_rows, num_cols)
        torch_tensor = torch_tensor.float()
        return torch_tensor
