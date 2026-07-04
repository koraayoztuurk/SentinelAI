// Investigation creation mutation hook (ES-047).
//
// A thin adapter over TanStack Query's mutation: creates an investigation and
// hands the created resource back to the caller (the landing page navigates
// to its workspace). No invalidation is needed — the resource is new.

import { useMutation } from "@tanstack/react-query";
import { ApiError, toApiError } from "../communication/errors";
import {
  createInvestigation,
  type InvestigationCreateInput,
  type InvestigationDto,
} from "../communication/investigations";

export interface CreateInvestigationState {
  readonly create: (input: InvestigationCreateInput) => void;
  readonly creating: boolean;
  readonly created: InvestigationDto | null;
  readonly error: ApiError | null;
}

export function useCreateInvestigation(
  onCreated?: (investigation: InvestigationDto) => void,
): CreateInvestigationState {
  const mutation = useMutation({
    mutationFn: createInvestigation,
    onSuccess: (investigation) => onCreated?.(investigation),
  });

  return {
    create: (input) => mutation.mutate(input),
    creating: mutation.isPending,
    created: mutation.data ?? null,
    error: toApiError(mutation.error),
  };
}
