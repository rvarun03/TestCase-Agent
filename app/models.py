from pydantic import BaseModel, Field, field_validator


class GenerateRequest(BaseModel):
    brd_text: str = Field(min_length=20, description="Pasted text from a BRD")


class TestCase(BaseModel):
    id: str
    title: str
    priority: str
    preconditions: list[str]
    test_data: list[str]
    steps: list[str]
    expected_result: str


class GenerateResponse(BaseModel):
    test_cases: list[TestCase]


class Requirement(BaseModel):
    id: str
    description: str

class RequirementAnalysis(BaseModel):
    requirements: list[Requirement]
    missing_details: list[str]

    @field_validator("requirements", mode="before")
    @classmethod
    def add_ids_to_string_requirements(cls, value: object) -> object:
        """Accept concise model output while preserving stable IDs downstream."""
        if not isinstance(value, list):
            return value

        return [
            {"id": f"FR-{index:02d}", "description": item}
            if isinstance(item, str)
            else item
            for index, item in enumerate(value, start=1)
        ]


class TestScenario(BaseModel):
    requirement_id: str
    scenario: str
    category: str

class ScenarioResponse(BaseModel):
    scenarios: list[TestScenario]
