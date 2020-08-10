from abc import ABC, abstractmethod
import torchvision
from data_hub.util.logger import logger
from typing import List
from data_hub.io.storage_connectors import StorageConnector
from data_hub.exception import DatasetFileCorruptError
import tempfile
import os
from data_hub.util.helper import calculate_md5
from data_hub.io.resources import ResourceFactory


class RetrieverFactory:

    @classmethod
    def get_http_retriever(cls, storage_connector: StorageConnector) -> "Retriever":
        retriever_impl = HTTPRetrieverImpl(storage_connector)
        return Retriever(retriever_impl)


class Retriever:

    def __init__(self, retriever_impl: "RetrieverImplIF"):
        self.retriever_impl = retriever_impl

    def retrieve(self, retrieval_jobs: List["RetrievalJob"]):
        self.retriever_impl.retrieve(retrieval_jobs)


class RetrievalJob:
    def __init__(self, identifier: str, source: str, md5_sum: str):
        self._identifier = identifier
        self._source = source
        self._md5_sum = md5_sum

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def source(self) -> str:
        return self._source

    @property
    def md5_sum(self) -> str:
        return self._md5_sum


class RetrieverImplIF(ABC):

    def __init__(self, storage_connector: StorageConnector):
        self.storage_connector = storage_connector

    @abstractmethod
    def retrieve(retrieval_jobs: List[RetrievalJob]):
        raise NotImplementedError


class HTTPRetrieverImpl(RetrieverImplIF):
    def __init__(self, storage_connector: StorageConnector):
        super().__init__(storage_connector)

    def _download_file(self, dest_folder: str, url: str, md5: str) -> str:
        """ Downloads a file given by the url.
        :param dest_path: destination path
        :param url: URL to the dataset
        :return: Path to downloaded file
        """
        logger.debug(f"Downloading data file from {url} ...")
        # download file
        filename = url.rpartition('/')[2]
        torchvision.datasets.utils.download_url(url, root=dest_folder, filename=filename)
        logger.debug("Done.")
        file_path = os.path.join(dest_folder, filename)
        with open(file_path, 'rb') as fd:
            calculated_md5_sum = calculate_md5(fd)
        if calculated_md5_sum != md5:
            logger.fat(f"Given MD5 hash did not match with the md5 has of file {file_path}")
            raise DatasetFileCorruptError
        return file_path

    def _download(self, retrieval_jobs: List[RetrievalJob], dest_folder: str) -> List[str]:
        file_paths = [self._download_file(
            url=retrieval_job.source, dest_folder=dest_folder, md5=retrieval_job.md5_sum) for retrieval_job in retrieval_jobs]
        return file_paths

    def retrieve(self, retrieval_jobs: List[RetrievalJob]):
        with tempfile.TemporaryDirectory() as tmp_dest_folder:
            logger.debug(f'Created temporary directory {tmp_dest_folder} for downloading resources...')
            # download dataset files
            tmp_resource_paths = self._download(retrieval_jobs, tmp_dest_folder)
            # store datset files
            for retrieval_job, tmp_resource_path in zip(retrieval_jobs, tmp_resource_paths):
                with open(tmp_resource_path, "rb") as fd:
                    resource = ResourceFactory.get_resource(
                        identifier=retrieval_job.identifier, file_like_object=fd, in_memory=False)
                    self.storage_connector.set_resource(identifier=retrieval_job.identifier, resource=resource)
