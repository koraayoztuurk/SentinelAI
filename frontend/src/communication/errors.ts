// Communication-layer error.
//
// `ApiError` is the typed, immutable failure surfaced by the API client. Its
// fields are `readonly` (the frontend equivalent of the backend's frozen-dataclass
// errors): once constructed, the error's code, message, request id and HTTP status
// never change.

export class ApiError extends Error {
  readonly code: string;
  readonly requestId: string | null;
  readonly status: number;

  constructor(
    code: string,
    message: string,
    status: number,
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.requestId = requestId;
    this.status = status;
    Object.freeze(this);
  }
}
