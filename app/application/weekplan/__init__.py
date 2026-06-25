"""WeekPlan use cases.

Each use case orchestrates load → mutate → persist → commit and returns the
resulting ``WeekPlan`` aggregate. Response/projection building is left to the
web layer so these handlers stay importable and unit-testable on their own.
"""
