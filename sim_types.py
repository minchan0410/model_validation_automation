from dataclasses import dataclass


@dataclass(frozen=True)
class TestCase:
    tc_id: str
    description: str
    input_times: list[float]
    input_values: list[float]
    stop_time: float
    test_req: list[str]


@dataclass(frozen=True)
class SimulationResult:
    tc_id: str
    description: str
    input_time: list[float]
    input_value: list[float]
    output_time: list[float]
    output_value: list[float]


@dataclass(frozen=True)
class RequirementResult:
    tc_id: str
    req_id: str
    passed: bool
