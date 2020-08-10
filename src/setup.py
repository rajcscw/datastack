from setuptools import find_packages, setup

setup(
    name='data_hub',
    version='0.0.1',
    packages=find_packages(),
    install_requires=["torch",
                      "torchvision",
                      "h5py",
                      "tqdm",
                      "flair"
                      ],
    python_requires=">=3.7"
)