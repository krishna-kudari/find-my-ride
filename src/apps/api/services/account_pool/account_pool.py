"Service Account Pool Management"
from typing import Optional
from .models import ServiceAccount

class AccountPool:
    "Service Account Pool Management"

    def create_service_accunt(
        self,
        phone_num: str,
        cred: str,
        client: str,
        status: Optional[str] = None
    ) -> ServiceAccount:
        """Create a new service account with validation.

        Args:
            phone_num: Phone number for the account
            cred: Headers json string
            client: Client identifier
            status: Account status (defaults to 'active')

        Returns:
            The created ServiceAccount instance

        Raises:
            ValueError: If required fields are empty
        """
        # Consolidate validation
        for field_name, field_value in [
            ("Phone number", phone_num),
            ("Credentials", cred),
            ("Client", client),
        ]:
            if not field_value:
                raise ValueError(f"{field_name} can't be empty")

        return ServiceAccount.objects.create(
            phone_num=phone_num,
            client=client,
            credentials=cred,
            status=status or "active",
            usage=0,
        )

    def get_service_account(self, client: str):
        account = ServiceAccount.objects.filter(client = client, status = "active").order_by("usage")[0]
        return account

