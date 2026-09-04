from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PaymentInitiationResult:
    provider_reference: str
    redirect_url: str | None = None


@dataclass(frozen=True)
class PaymentVerificationResult:
    success: bool
    provider_transaction_id: str | None = None
    failure_code: str = ""
    failure_message: str = ""
    raw_response: dict[str, Any] | None = None


class PaymentGateway(ABC):
    name: str

    @abstractmethod
    def initiate_payment(
        self,
        *,
        payment,
        attempt,
    ) -> PaymentInitiationResult:
        raise NotImplementedError

    @abstractmethod
    def verify_payment(
        self,
        *,
        attempt,
        payload: dict[str, Any],
    ) -> PaymentVerificationResult:
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(
        self,
        *,
        payload: dict[str, Any],
        signature: str | None = None,
    ) -> None:
        raise NotImplementedError