
import pathlib

from setuptools import setup

HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
  name = 'auto_related',        
  packages = ['auto_related'],   
  version = '0.0.3',      
  license='MIT',
  description = 'Optimize serializers automatically with select_related(), prefetch_related(), defer() and only()',   # Give a short description about your library
  long_description=README,
  long_description_content_type="text/markdown",
  author = 'Furkan Akyol',                   
  author_email = 'furkanakyol1997@gmail.com',     
  url = 'https://github.com/thetarby/django-auto-related',   
  #download_url 
  keywords = ['django', 'djangorest', 'related', 'select', 'prefetch', 'defer', 'only'],  
  install_requires=[            
          'djangorestframework',
          'django',
      ],
  classifiers=[
    'Development Status :: 4 - Beta',      
    'Intended Audience :: Developers',      
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',   
    'Programming Language :: Python :: 3', 
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
  ],
)