"""Relational Circom/Solidity binding analysis.

The public entrypoint is deliberately separate from the P1--P5 analyzer.  It
compares producer enforcement with consumer reliance and never imports test
expectations or application labels.
"""

from .analyzer import DIMENSIONS, analyze_relational

__all__ = ["DIMENSIONS", "analyze_relational"]
