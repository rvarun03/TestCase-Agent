from pydantic import BaseModel, Field


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


class TestScenario(BaseModel):
    requirement_id: str
    scenario: str
    category: str

class ScenarioResponse(BaseModel):
    scenarios: list[TestScenario]