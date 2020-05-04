import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

# Parse version from _version.py in package directory
# See https://packaging.python.org/guides/single-sourcing-package-version/#single-sourcing-the-version
version = {}
with open('src/mortimer/_version.py') as f:
    exec(f.read(), version)

setuptools.setup(
    name="mortimer",
    version=version["__version__"],
    author="Christian Treffenstädt, Paul Wiemann, Johannes Brachem",
    author_email="treffenstaedt@psych.uni-goettingen.de",
    description="A web-app for the administration of alfred experiments.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ctreffe/mortimer",
    packages=setuptools.find_packages(),
    package_data={
        "mortimer": [
            "static/*",
            "static/futurizing_alfred_scripts/*"
            "static/css/*",
            "static/img/*",
            "static/js/*",
            "templates/*",
            "templates/elements/*",
        ]
    },
    package_dir={"": "src"},
    install_requires=[
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)

