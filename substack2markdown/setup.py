"""
Setup script for Substack2Markdown.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / 'README.md'
long_description = readme_path.read_text(encoding='utf-8') if readme_path.exists() else ''

# Read requirements
requirements_path = Path(__file__).parent / 'requirements.txt'
requirements = []
if requirements_path.exists():
    requirements = [
        line.strip() 
        for line in requirements_path.read_text().split('\n')
        if line.strip() and not line.startswith('#')
    ]

setup(
    name='substack2markdown',
    version='1.0.0',
    description='Download Substack publications to Markdown format',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/substack2markdown',
    license='MIT',
    
    py_modules=[
        'main',
        'config',
        'browser',
        'scraper',
        'converter',
        'utils',
    ],
    
    install_requires=requirements,
    
    python_requires='>=3.8',
    
    entry_points={
        'console_scripts': [
            'substack2markdown=main:main',
        ],
    },
    
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Text Processing :: Markup',
        'Topic :: Utilities',
    ],
    
    keywords='substack markdown converter scraper backup archive',
)
