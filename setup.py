from setuptools import setup

setup(
    name="safe-file-walker",
    version="1.0.0",
    description="Secure filesystem traversal with hardlink deduplication and DoS protection",
    author="saiconfirst",
    author_email="your@email.com",  # ← замените на ваш email
    url="https://github.com/saiconfirst/safe-file-walker",
    py_modules=["safe_file_walker"],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
        "Topic :: System :: Filesystems",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="filesystem security traversal hardlink symlink dos-protection",
    license="MIT",
)