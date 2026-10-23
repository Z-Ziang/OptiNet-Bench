"""Native Inspect task; private answers are only read by the scorer or offline solver."""
import json

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, ModelOutput
from inspect_ai.scorer import Score, scorer
from inspect_ai.solver import generate, solver

from optinet.data import plan_rows, public_messages, reference
from optinet.scoring import score_answer


@scorer(metrics=[])
def frozen_scoring():
    async def score(state, target):
        result = score_answer(state.metadata["case_record"], state.output.completion)
        category = result["relaxed"]["category"]
        return Score(value=category, answer=category, metadata=result)
    return score


@solver
def offline_reference_replay():
    async def solve(state, generate):
        answer = reference(state.metadata["case_record"])
        state.output = ModelOutput.from_content(model="offline/reference_replay", content=json.dumps(answer))
        return state
    return solve


@task
def optinet_cases(plan_path: str, offline_reference: bool = False):
    samples = []
    for row in plan_rows(plan_path):
        messages = [(ChatMessageSystem if item["role"] == "system" else ChatMessageUser)(content=item["content"])
                    for item in public_messages(row)]
        samples.append(Sample(id=row["case_uid"], input=messages, target="", metadata={"case_record": row}))
    return Task(dataset=samples, solver=offline_reference_replay() if offline_reference else generate(),
                scorer=frozen_scoring(), version="OPTINET_NINE_TASKS_V1")
