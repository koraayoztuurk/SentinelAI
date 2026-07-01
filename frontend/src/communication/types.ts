// API envelope types.
//
// These mirror the backend's standard response envelope (ES-014, api-design §9):
// every response carries a status, a metadata block and either a typed `data`
// payload or a structured `error`. Mirroring the contract keeps frontend
// communication type-safe against the Backend API.

export interface ResponseMeta {
  readonly request_id: string;
  readonly correlation_id: string;
  readonly timestamp: string;
  readonly api_version: string;
}

export interface ApiSuccess<T> {
  readonly status: "success";
  readonly data: T;
  readonly meta: ResponseMeta;
}

export interface ApiErrorBody {
  readonly code: string;
  readonly message: string;
}

export interface ApiErrorResponse {
  readonly status: "error";
  readonly error: ApiErrorBody;
  readonly meta: ResponseMeta;
}
