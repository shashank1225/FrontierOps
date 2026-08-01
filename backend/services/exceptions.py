import uuid


class ApplicationServiceError(Exception):
    """Base exception for application-management use cases."""


class ApplicationAlreadyExistsError(ApplicationServiceError):
    def __init__(self, name: str) -> None:
        super().__init__(f"An AI application named '{name}' already exists.")


class ApplicationNotFoundError(ApplicationServiceError):
    def __init__(self, application_id: uuid.UUID) -> None:
        super().__init__(f"AI application '{application_id}' was not found.")


class EvaluationDatasetNotFoundError(ApplicationServiceError):
    def __init__(self, dataset_id: uuid.UUID) -> None:
        super().__init__(f"Evaluation dataset '{dataset_id}' was not found.")


class EvaluationDatasetAlreadyExistsError(ApplicationServiceError):
    def __init__(self, name: str) -> None:
        super().__init__(f"An evaluation dataset named '{name}' already exists.")
