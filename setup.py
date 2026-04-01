from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = [line.strip() for line in f if line.strip()]

setup(
    name="school_statements",
    version="0.0.1",
    description="School statements and bulk statement generation for ERPNext",
    author="OpenAI",
    author_email="support@example.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
