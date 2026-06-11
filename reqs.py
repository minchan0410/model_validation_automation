from sim_types import RequirementResult, SimulationResult


def find_step_index(result: SimulationResult) -> list[int]:
    """입력 변화(step)가 발생하는 지점을 모두 찾는 함수"""
    change_indexs: list[int] = []

    for index in range(1, len(result.input_value)):
        if abs(result.input_value[index] - result.input_value[index - 1]) > 0.01:
            change_indexs.append(index)

    return change_indexs


def req_001(result: SimulationResult) -> RequirementResult:
    """req 001. 오버슈트는 1% 이내여야 한다"""
    change_indexs = find_step_index(result)

    if len(change_indexs) == 0:
        return RequirementResult(
            tc_id=result.tc_id,
            req_id="REQ_001",
            passed=False,
        )

    for idx in range(len(change_indexs)):
        start_index = change_indexs[idx]

        if idx + 1 < len(change_indexs):
            end_index = change_indexs[idx + 1]
        else:
            end_index = len(result.output_value)

        previous_input = result.input_value[start_index - 1]
        target_input = result.input_value[start_index]
        tol = abs(target_input - previous_input) * 0.01

        if target_input > previous_input:
            for check_idx in range(start_index, end_index):
                if result.output_value[check_idx] > target_input + tol:
                    return RequirementResult(
                        tc_id=result.tc_id,
                        req_id="REQ_001",
                        passed=False,
                    )

        elif target_input < previous_input:
            for check_idx in range(start_index, end_index):
                if result.output_value[check_idx] < target_input - tol:
                    return RequirementResult(
                        tc_id=result.tc_id,
                        req_id="REQ_001",
                        passed=False,
                    )

    return RequirementResult(
        tc_id=result.tc_id,
        req_id="REQ_001",
        passed=True,
    )


def req_002(result: SimulationResult) -> RequirementResult:
    """req 002. 각도 오차 1도 이내 정착시간은 1초 이하여야 한다."""
    change_indexs = find_step_index(result)

    if len(change_indexs) == 0:
        return RequirementResult(
            tc_id=result.tc_id,
            req_id="REQ_002",
            passed=False,
        )

    for idx in range(len(change_indexs)):
        start_index = change_indexs[idx]

        if idx + 1 < len(change_indexs):
            end_index = change_indexs[idx + 1]
        else:
            end_index = len(result.output_value)

        target_input = result.input_value[start_index]
        settled = False

        for check_idx in range(start_index, end_index):
            error = abs(target_input - result.output_value[check_idx])

            if error <= 1.0:
                in_band = True

                for remain_idx in range(check_idx, end_index):
                    remain_error = abs(target_input - result.output_value[remain_idx])
                    if remain_error > 1.0:
                        in_band = False
                        break

                if in_band:
                    settling_time = result.output_time[check_idx] - result.output_time[start_index]

                    if settling_time > 1.0:
                        return RequirementResult(
                            tc_id=result.tc_id,
                            req_id="REQ_002",
                            passed=False,
                        )

                    settled = True
                    break

        if not settled:
            return RequirementResult(
                tc_id=result.tc_id,
                req_id="REQ_002",
                passed=False,
            )

    return RequirementResult(
        tc_id=result.tc_id,
        req_id="REQ_002",
        passed=True,
    )


def req_003(result: SimulationResult) -> RequirementResult:
    for res in result.output_value:
        if res > 30.0 or res < -30.0:
            return RequirementResult(
                tc_id=result.tc_id,
                req_id="REQ_003",
                passed=False,
            )

    return RequirementResult(
        tc_id=result.tc_id,
        req_id="REQ_003",
        passed=True,
    )


def evaluate_requirements(
    result: SimulationResult,
    req_ids: list[str],
) -> list[RequirementResult]:
    """지정한 요구사항만 골라서 검증한다."""
    req_map = {
        "REQ_001": req_001,
        "REQ_002": req_002,
        "REQ_003": req_003,
    }

    results: list[RequirementResult] = []

    for req_id in req_ids:
        if req_id not in req_map:
            raise ValueError(f"Unknown requirement id: {req_id}")

        results.append(req_map[req_id](result))

    return results
