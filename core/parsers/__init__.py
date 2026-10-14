"""File parsing and extraction package."""

from core.parsers.html_parser import parse_html_file, parse_html_table

__all__ = [
    "parse_html_table",
    "parse_html_file",
]
