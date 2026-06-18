import logging
from typing import Optional, Dict
from .. import config
from ..utils import secrets_manager
from . import machine_to_machine
import requests

logger = logging.getLogger(__name__)

class CompanyClient:
    """Client for Company API to retrieve company information."""

    def __init__(self, base_url: Optional[str] = None):
        self._base_url = base_url or config.COMPANY_API
        self._token = machine_to_machine.get_token()
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json"
        })

    def _get_auth_headers(self) -> Dict[str, str]:
        """Build headers with authorization."""
        headers = {"X-User-Id": "VAAS_BANCOLOMBIA_NEW_SCRAPPER"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        else:
            logger.warning("No M2M token available for Authorization header")

        VAAS_HEADER = secrets_manager.get_secret_value("VAAS_HEADER")
        if VAAS_HEADER:
            headers["x-only-for-vaas"] = VAAS_HEADER
            logger.info("VAAS_HEADER successfully retrieved and added to headers")
        else:
            logger.warning("VAAS_HEADER not found in secrets manager")

        return headers

    def get_borrower_id_by_code(self, code: str) -> Optional[int]:
        """
        Get borrower ID by company code.

        Args:
            code: The company code (e.g., ADDI)

        Returns:
            The borrower ID (int) if found, None otherwise.
        """
        try:
            # External API for company lookup
            url = self._base_url
            logger.info(">>> ABOUT TO GET AUTH HEADERS <<<")
            headers = self._get_auth_headers()
            logger.info(">>> GOT AUTH HEADERS <<<")
            logger.info(f">>> HEADERS KEYS: {list(headers.keys())} <<<")
            
            logger.info(f"Making request to {url} with params code={code}")
            logger.info(f"Request headers (keys only): {list(headers.keys())}")

            response = self._session.get(
                url,
                params={"code": code},
                headers=headers
            )

            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response content-type: {response.headers.get('content-type', 'N/A')}")

            response.raise_for_status()

            try:
                data = response.json()
            except ValueError as e:
                logger.error(f"Failed to parse JSON response from {url}: {e}. Response body snippet: {response.text[:200]}")
                return None

            # Response is a list of companies
            if data and isinstance(data, list) and len(data) > 0:
                company = data[0]
                return company.get("id")

            logger.warning(f"Borrower not found for code {code}")
            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching borrower ID for code {code}: {e}")
            raise

    def get_company_by_id(self, borrower_id: int) -> Optional[str]:
        """
        Get company code by borrower/company id (inverse of get_borrower_id_by_code).

        Args:
            borrower_id: The company/borrower id (e.g., 143).

        Returns:
            The company code (str) if found, None otherwise.
        """
        try:
            url = self._base_url
            headers = self._get_auth_headers()

            logger.info(f"Making request to {url} with params id={borrower_id}")

            response = self._session.get(
                url,
                params={"id": borrower_id},
                headers=headers,
            )

            logger.info(f"Response status code: {response.status_code}")
            response.raise_for_status()

            try:
                data = response.json()
            except ValueError as e:
                logger.error(f"Failed to parse JSON response from {url}: {e}. Response body snippet: {response.text[:200]}")
                return None

            # Response is a list of companies
            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get("code")

            logger.warning(f"Company not found for id {borrower_id}")
            return None

        except requests.RequestException as e:
            logger.error(f"Error fetching company code for id {borrower_id}: {e}")
            raise
