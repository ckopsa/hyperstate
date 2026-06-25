"""Recipe use cases.

Each use case orchestrates load → mutate → persist → commit and returns the
resulting ``Recipe`` aggregate. Response/projection building is intentionally
left to the web layer (see bead dp-1zv: recipes projections, routes & wiring),
so these handlers stay importable and unit-testable without the projection
layer in place.
"""
