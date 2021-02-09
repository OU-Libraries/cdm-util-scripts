from setuptools import setup, find_packages

# setup patterned after _Python Testing with pytest_ (Okken, 2017), "Creating an Installable Package"
setup(
    name='cdm-util-scripts',
    version='0.3.3',
    description="Ohio University CONTENTdm utility scripts",
    url='https://github.com/OU-Libraries/cdm-util-scripts',
    author='Nick Ver Steegh',
    author_email='versteeg@ohio.edu',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=['requests', 'jinja2'],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'catcherdiff=catcherdiff.catcherdiff:main',
            'csv2catcher=csv2catcher.csv2catcher:main',
            'csv2json=csv2json.csv2json:main',
            'ftp2catcher=ftp2catcher.ftp2catcher:main',
            'ftpfields2catcher=ftpfields2catcher.ftpfields2catcher:main',
            'printcdminfo=printcdminfo.printcdminfo:main',
            'printftpinfo=printftpinfo.printftpinfo:main',
            'scanftpfields=scanftpfields.scanftpfields:main',
        ]
    }
)
