import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from reqs import evaluate_requirements
from sim_types import RequirementResult, SimulationResult, TestCase


ENGINE_DIST = Path(r"C:\temp\matlab_engine_py311\dist")

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_NAME = "dc_motor_position"
MODEL_FILE = SCRIPT_DIR / f"{MODEL_NAME}.slx"
OUTPUT_DIR = SCRIPT_DIR / "outputs"

FROM_WORKSPACE_BLOCK = f"{MODEL_NAME}/From Workspace"
OUTPUT_TO_WORKSPACE_BLOCK = f"{MODEL_NAME}/To Workspace"
INPUT_TO_WORKSPACE_BLOCK = f"{MODEL_NAME}/To Workspace1"


if ENGINE_DIST.is_dir() and str(ENGINE_DIST) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIST))

import matlab
import matlab.engine


def build_test_cases() -> list[TestCase]:
    """Return the default regression test cases."""
    return [
        TestCase(
            tc_id="TC_001",
            description="Positive 10 deg step",
            input_times=[0.0, 0.9999, 1.0, 11.0],
            input_values=[0.0, 0.0, 10.0, 10.0],
            stop_time=10.0,
            test_req=["REQ_001", "REQ_002"],
        ),
        TestCase(
            tc_id="TC_002",
            description="Negative 10 deg step",
            input_times=[0.0, 0.9999, 1.0, 11.0],
            input_values=[0.0, 0.0, -30.0, -30.0],
            stop_time=10.0,
            test_req=["REQ_001", "REQ_002"],
        ),
        TestCase(
            tc_id="TC_003",
            description="Positive 30 deg step",
            input_times=[0.0, 0.9999, 1.0, 11.0],
            input_values=[0.0, 0.0, 30.0, 30.0],
            stop_time=10.0,
            test_req=["REQ_001", "REQ_002", "REQ_003"],
        ),
        TestCase(
            tc_id="TC_004",
            description="Negative -30 deg step",
            input_times=[0.0, 0.9999, 1.0, 11.0],
            input_values=[0.0, 0.0, -30.0, -30.0],
            stop_time=10.0,
            test_req=["REQ_001", "REQ_002", "REQ_003"],
        ),
        TestCase(
            tc_id="TC_005",
            description="check maximum/minimum 1",
            input_times=[0.0, 0.999, 1.0, 3.999, 4.0, 6.999, 7.0, 11.0],
            input_values=[0.0, 0.0, 20.0, 20.0, 40.0, 40.0, 20.0, 20.0],
            stop_time=10.0,
            test_req=["REQ_003"],
        ),
        TestCase(
            tc_id="TC_006",
            description="check maximum/minimum 2",
            input_times=[0.0, 0.999, 1.0, 3.999, 4.0, 6.999, 7.0, 11.0],
            input_values=[0.0, 0.0, -20.0, -20.0, -40.0, -40.0, -20.0, -20.0],
            stop_time=10.0,
            test_req=["REQ_003"],
        ),
        TestCase(
            tc_id="TC_007",
            description="multi step 1",
            input_times=[0.0, 0.999, 1.0, 3.999, 4.0, 6.999, 7.0, 11.0],
            input_values=[0.0, 0.0, 10.0, 10.0, 20.0, 20.0, 30.0, 30.0],
            stop_time=10.0,
            test_req=["REQ_001", "REQ_002", "REQ_003"],
        ),
        TestCase(
            tc_id="TC_008",
            description="multi step 2",
            input_times=[0.0, 0.999, 1.0, 3.499, 3.5, 6.499, 6.5, 11.0],
            input_values=[0.0, 0.0, -30.0, -30.0, 30.0, 30.0, -30.0, -30.0],
            stop_time=10.0,
            test_req=["REQ_001", "REQ_002", "REQ_003"],
        ),
    ]


def to_matlab_column(values: list[float]):
    """Convert a Python 1D list to a MATLAB column vector."""
    return matlab.double([[float(value)] for value in values])


def matlab_column_to_list(values) -> list[float]:
    """Convert a MATLAB column vector returned by Engine into floats."""
    result: list[float] = []

    for row in values:
        if isinstance(row, (list, tuple)):
            result.append(float(row[0]))
            continue

        try:
            result.append(float(row))
        except (TypeError, ValueError):
            result.append(float(row[0]))

    return result


def configure_model(eng: matlab.engine.MatlabEngine) -> None:
    """Configure the Simulink model before running test cases."""
    eng.cd(str(SCRIPT_DIR), nargout=0)
    eng.load_system(str(MODEL_FILE), nargout=0)

    eng.set_param(
        FROM_WORKSPACE_BLOCK,
        "VariableName", "simin",
        "Interpolate", "on",
        "SampleTime", "0.001",
        nargout=0,
    )

    eng.set_param(
        OUTPUT_TO_WORKSPACE_BLOCK,
        "VariableName", "simout",
        "SaveFormat", "Timeseries",
        "SampleTime", "-1",
        nargout=0,
    )

    eng.set_param(
        INPUT_TO_WORKSPACE_BLOCK,
        "VariableName", "ref_deg",
        "SaveFormat", "Timeseries",
        "SampleTime", "-1",
        nargout=0,
    )

    eng.set_param(MODEL_NAME, "ReturnWorkspaceOutputs", "on", nargout=0)


def run_simulation(eng: matlab.engine.MatlabEngine, test_case: TestCase) -> SimulationResult:
    """Run one test case and return the simulation result."""
    if len(test_case.input_times) != len(test_case.input_values):
        raise ValueError(f"{test_case.tc_id}: input_times and input_values length mismatch")

    eng.workspace["step_times"] = to_matlab_column(test_case.input_times)
    eng.workspace["step_values"] = to_matlab_column(test_case.input_values)
    eng.eval(
        "simin = timeseries(step_values, step_times, 'Name', 'ref_deg');"
        "clear step_times step_values",
        nargout=0,
    )

    eng.eval("clear simOut t_out p_out t_in p_in", nargout=0)
    eng.eval(
        f"simOut = sim('{MODEL_NAME}', 'StopTime', '{test_case.stop_time}');"
        "t_out = simOut.simout.Time;"
        "p_out = simOut.simout.Data;"
        "t_in = simOut.ref_deg.Time;"
        "p_in = simOut.ref_deg.Data;",
        nargout=0,
    )

    output_time = matlab_column_to_list(eng.workspace["t_out"])
    output_value = matlab_column_to_list(eng.workspace["p_out"])
    input_time = matlab_column_to_list(eng.workspace["t_in"])
    input_value = matlab_column_to_list(eng.workspace["p_in"])

    result = SimulationResult(
        tc_id=test_case.tc_id,
        description=test_case.description,
        input_time=input_time,
        input_value=input_value,
        output_time=output_time,
        output_value=output_value,
    )

    save_case_outputs(result)
    return result


def save_series_csv(path: Path, time_values: list[float], signal_values: list[float]) -> None:
    """Save one time-series to CSV."""
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["time_s", "value"])
        writer.writerows(
            (f"{time_value:.3f}", f"{signal_value:.3f}")
            for time_value, signal_value in zip(time_values, signal_values)
        )


def save_case_outputs(result: SimulationResult) -> None:
    """Save the input/output traces for one test case."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_series_csv(OUTPUT_DIR / f"{result.tc_id}_input.csv", result.input_time, result.input_value)
    save_series_csv(OUTPUT_DIR / f"{result.tc_id}_output.csv", result.output_time, result.output_value)


def requirement_table(results: list[RequirementResult]) -> None:
    """Show a simple colored requirement-vs-testcase table."""
    tc_ids = []
    req_ids = []
    result_map = {}

    for result in results:
        if result.tc_id not in tc_ids:
            tc_ids.append(result.tc_id)
        if result.req_id not in req_ids:
            req_ids.append(result.req_id)
        result_map[(result.req_id, result.tc_id)] = result.passed

    cell_text = []
    cell_colors = []

    for req_id in req_ids:
        text_row = []
        color_row = []

        for tc_id in tc_ids:
            passed = result_map.get((req_id, tc_id))

            if passed is True:
                text_row.append("PASS")
                color_row.append("#7CFC8A")
            elif passed is False:
                text_row.append("FAIL")
                color_row.append("#FF7C7C")
            else:
                text_row.append("-")
                color_row.append("#D9D9D9")

        cell_text.append(text_row)
        cell_colors.append(color_row)

    fig_width = max(4, len(tc_ids) * 1.5)
    fig_height = max(3, len(req_ids) * 0.8 + 1.5)

    plt.figure(figsize=(fig_width, fig_height))
    plt.title("Requirement Verification Matrix")
    plt.axis("off")

    table = plt.table(
        cellText=cell_text,
        cellColours=cell_colors,
        rowLabels=req_ids,
        colLabels=tc_ids,
        cellLoc="center",
        loc="center",
    )
    table.scale(1, 2)

    plt.tight_layout()
    plt.show()


def main() -> None:
    test_cases = build_test_cases() # 테스트 케이스 생성
    test_results = []

    eng = matlab.engine.start_matlab() # 매트랩 엔진을 통해 매트랩 구동
    try:
        configure_model(eng) # 블럭 파라미터 재정의(To workspace, from workspace)

        for test_case in test_cases: # TC를 통해 시뮬레이션 수행 및 결과 확인
            simulation_result = run_simulation(eng, test_case)
            req_test_results = evaluate_requirements(simulation_result, test_case.test_req)
            test_results.extend(req_test_results)

        requirement_table(test_results)

    finally:
        eng.eval(f"if bdIsLoaded('{MODEL_NAME}'), close_system('{MODEL_NAME}', 0); end", nargout=0) # 모델 종료
        eng.quit() # 매트랩 종료


if __name__ == "__main__":
    main()
