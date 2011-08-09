from setuptools import setup, find_packages

setup(name="geventirc",
      version="0.1dev",
      author="Antonin Amand (@gwik)",
      author_email="antonin.amand@gmail.com",
      description="gevent based irc client",
      namespace_packages=['geventirc'],
      package_dir = {'':'lib'},
      packages=find_packages('lib'),
      zip_safe=False,
      install_requires=[
          'distribute',
          'gevent',
        ],
    )

