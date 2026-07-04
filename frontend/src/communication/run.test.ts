import { describe, expect, it } from "vitest";
import { toRunOutcomeViewModel } from "./run";

describe("toRunOutcomeViewModel", () => {
  it("maps the outcome summary and its actions", () => {
    const viewModel = toRunOutcomeViewModel({
      end: "escalated",
      cycles: 2,
      failure_code: "ai.llm_provider_error",
      actions: [
        {
          action_id: "act-1",
          target: "graph",
          execution_status: "failed",
          error_code: "graph.store_unavailable",
        },
      ],
    });

    expect(viewModel.end).toBe("escalated");
    expect(viewModel.cycles).toBe(2);
    expect(viewModel.failureCode).toBe("ai.llm_provider_error");
    expect(viewModel.actions).toEqual([
      {
        executionStatus: "failed",
        target: "graph",
        errorCode: "graph.store_unavailable",
      },
    ]);
  });
});
