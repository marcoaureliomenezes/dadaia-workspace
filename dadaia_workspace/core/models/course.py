"""Course domain model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Course:
    slug: str
    name: str
    module_number: int
    module_name: str
    created_at: str
    course_dir: str
