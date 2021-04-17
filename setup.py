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
    author_email="alfred@psych.uni-goettingen.de",
    description="A web-appication for the administration of alfred experiments.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ctreffe/mortimer",
    packages=setuptools.find_packages("src"),
    package_data={
        "mortimer": [
            "static/*",
            "static/futurizing_alfred_scripts/*",
            "static/css/*",
            "static/img/*",
            "static/js/*",
            "templates/*",
            "templates/elements/*",
            "templates/errors/*",
            "templates/additional/*"
        ]
    },
    package_dir={"": "src"},
    install_requires=[
        "alfred3>=2.0",
        "cryptography>=3.4",
        "email_validator>=1.1",
        "flask>=1.1.2",
        "flask_bcrypt>=0.7.1",
        "flask_dropzone>=1.5.4",
        "flask_login>=0.5.0",
        "flask_mail>=0.9.1",
        "flask_mongoengine>=0.9.5",
        "flask-wtf>=0.14.3",
        "pymongo>=3.10"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)

