from distutils.core import setup


setup(
    name = "django-optimizations",
    version = "1.0.4",
    description = "A utility library for Django aimed at improving website performance.",
    author = "Dave Hall",
    author_email = "dave@etianen.com",
    url = "https://github.com/etianen/django-optimizations",
    zip_safe = False,
    packages = [
        "optimizations",
        "optimizations.templatetags",
        "optimizations.management",
        "optimizations.management.commands",
    ],
    package_dir = {
        "": "src",
    },
    package_data = {
        "optimizations": [
            "locale/*/LC_MESSAGES/django.*",
            "templates/assets/*.html",
            "resources/*.jar",
        ],
    },
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Framework :: Django",
    ],
)